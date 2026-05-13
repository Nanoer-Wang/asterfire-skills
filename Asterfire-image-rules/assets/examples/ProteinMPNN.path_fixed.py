import os
import shutil
import glob
import json
import zipfile
import subprocess
from datetime import datetime
from pathlib import Path

from adam_community.tool import Tool
from adam_community.tool_types import MDFile, tool_io
from adam_community.util import execCmd


@tool_io(
    outputs={
        "output_zip": str,
        "report": MDFile,
        "success": bool,
    }
)
class runner(Tool):
    """ProteinMPNN蛋白质序列设计Kit入口。

    传入蛋白质骨架PDB文件，使用ProteinMPNN进行逆向序列预测，
    支持序列生成、评分、条件/无条件概率计算等多种模式。
    """

    DISPLAY_NAME = "ProteinMPNN蛋白质序列设计"
    NETWORK = False
    CPU = 4
    GPU = 1
    SIF = "ProteinMPNN:1.0.0"

    def call(self, kwargs):
        args = kwargs["args"]
        cwd = Path.cwd()

        # ---------- 1. 读取所有参数 ----------
        input_pdb = self._as_path(args.get("input_pdb", ""))
        mode = args.get("mode", "design")
        chains_to_design = args.get("chains_to_design", "").strip()
        model_name = args.get("model_name", "v_48_020")
        use_soluble_model = args.get("use_soluble_model", False)
        ca_only = args.get("ca_only", False)
        num_seq_per_target = args.get("num_seq_per_target", 1)
        sampling_temp = args.get("sampling_temp", "0.1")
        batch_size = args.get("batch_size", 1)
        seed = args.get("seed", 0)
        backbone_noise = args.get("backbone_noise", 0.0)
        save_score = args.get("save_score", False)
        save_probs = args.get("save_probs", False)
        fixed_positions = args.get("fixed_positions", "").strip()
        specify_non_fixed = args.get("specify_non_fixed", False)
        tied_positions = args.get("tied_positions", "").strip()
        homooligomer = args.get("homooligomer", False)
        omit_AAs = args.get("omit_AAs", "X").strip()
        fasta_sequence = args.get("fasta_sequence", "").strip()
        pssm_multi = args.get("pssm_multi", 0.0)
        pssm_threshold = args.get("pssm_threshold", 0.0)
        pssm_bias_flag = args.get("pssm_bias_flag", False)
        pssm_log_odds_flag = args.get("pssm_log_odds_flag", False)

        # 高级JSONL配置文件
        bias_AA_jsonl = args.get("bias_AA_jsonl", "")
        bias_by_res_jsonl = args.get("bias_by_res_jsonl", "")
        omit_AA_jsonl_file = args.get("omit_AA_jsonl_file", "")
        pssm_jsonl_file = args.get("pssm_jsonl_file", "")

        print(f"[ProteinMPNN] 当前工作目录: {cwd}")
        print(f"[ProteinMPNN] 输入PDB: {input_pdb}")
        print(f"[ProteinMPNN] 运行模式: {mode}")
        print(f"[ProteinMPNN] 模型: {model_name}")
        print(
            f"[ProteinMPNN] 参数摘要: ca_only={ca_only}, soluble={use_soluble_model}, "
            f"num_seq={num_seq_per_target}, temp={sampling_temp}"
        )

        # ---------- 2. 输入存在性检查 ----------
        if not input_pdb or not input_pdb.exists():
            raise FileNotFoundError(f"输入PDB文件不存在或路径无效: {input_pdb}")

        # ---------- 3. 准备工作目录 ----------
        work_dir = cwd / "proteinmpnn_work"
        work_dir.mkdir(exist_ok=True)

        pdb_basename = input_pdb.name
        work_pdb_path = work_dir / pdb_basename
        shutil.copy2(input_pdb, work_pdb_path)

        output_dir = work_dir / "outputs"
        output_dir.mkdir(exist_ok=True)

        mpnn_dir = Path(os.environ.get("PROTEINMPNN_HOME", "/opt/ProteinMPNN"))
        if not mpnn_dir.is_dir():
            raise FileNotFoundError(
                f"镜像内 ProteinMPNN 项目目录不存在: {mpnn_dir}. "
                "请检查 Dockerfile 的 COPY 目标路径或 PROTEINMPNN_HOME 环境变量。"
            )

        required_image_files = [
            mpnn_dir / "protein_mpnn_run.py",
            mpnn_dir / "helper_scripts" / "parse_multiple_chains.py",
            mpnn_dir / "helper_scripts" / "assign_fixed_chains.py",
            mpnn_dir / "helper_scripts" / "make_fixed_positions_dict.py",
            mpnn_dir / "helper_scripts" / "make_tied_positions_dict.py",
        ]
        for fp in required_image_files:
            if not fp.exists():
                raise FileNotFoundError(f"镜像内 ProteinMPNN 必要文件不存在: {fp}")

        # ---------- 4. 构建命令链 ----------
        parsed_chains = output_dir / "parsed_pdbs.jsonl"
        chain_id_jsonl = ""
        fixed_positions_jsonl = ""
        tied_positions_jsonl = ""

        cmd_parts = []

        # 4.1 解析PDB
        parse_cmd = (
            f"python helper_scripts/parse_multiple_chains.py "
            f"--input_path={work_dir} --output_path={parsed_chains}"
        )
        if ca_only:
            parse_cmd += " --ca_only"
        cmd_parts.append(parse_cmd)

        # 4.2 分配设计链
        if chains_to_design:
            chain_id_jsonl = output_dir / "assigned_chains.jsonl"
            assign_cmd = (
                f"python helper_scripts/assign_fixed_chains.py "
                f'--input_path={parsed_chains} --output_path={chain_id_jsonl} '
                f'--chain_list="{chains_to_design}"'
            )
            cmd_parts.append(assign_cmd)

        # 4.3 固定位置
        if fixed_positions and chains_to_design:
            fixed_positions_jsonl = output_dir / "fixed_positions.jsonl"
            fixed_cmd = (
                f"python helper_scripts/make_fixed_positions_dict.py "
                f'--input_path={parsed_chains} --output_path={fixed_positions_jsonl} '
                f'--chain_list="{chains_to_design}" '
                f'--position_list="{fixed_positions}"'
            )
            if specify_non_fixed:
                fixed_cmd += " --specify_non_fixed"
            cmd_parts.append(fixed_cmd)

        # 4.4 对称/绑定位置
        if tied_positions and chains_to_design and not homooligomer:
            tied_positions_jsonl = output_dir / "tied_positions.jsonl"
            tied_cmd = (
                f"python helper_scripts/make_tied_positions_dict.py "
                f'--input_path={parsed_chains} --output_path={tied_positions_jsonl} '
                f'--chain_list="{chains_to_design}" '
                f'--position_list="{tied_positions}"'
            )
            cmd_parts.append(tied_cmd)
        elif homooligomer:
            tied_positions_jsonl = output_dir / "tied_positions.jsonl"
            tied_cmd = (
                f"python helper_scripts/make_tied_positions_dict.py "
                f"--input_path={parsed_chains} --output_path={tied_positions_jsonl} "
                f"--homooligomer 1"
            )
            cmd_parts.append(tied_cmd)

        # 4.5 主运行命令
        run_cmd = (
            f"python protein_mpnn_run.py --jsonl_path {parsed_chains} "
            f"--out_folder {output_dir}"
        )

        if chain_id_jsonl:
            run_cmd += f" --chain_id_jsonl {chain_id_jsonl}"
        if fixed_positions_jsonl:
            run_cmd += f" --fixed_positions_jsonl {fixed_positions_jsonl}"
        if tied_positions_jsonl:
            run_cmd += f" --tied_positions_jsonl {tied_positions_jsonl}"

        # 运行模式
        if mode == "score_only":
            run_cmd += " --score_only 1"
            if fasta_sequence:
                fasta_path = work_dir / "input.fasta"
                with open(fasta_path, "w", encoding="utf-8") as f:
                    f.write(f">input\n{fasta_sequence}\n")
                run_cmd += f" --path_to_fasta {fasta_path}"
        elif mode == "conditional_probs":
            run_cmd += " --conditional_probs_only 1"
        elif mode == "unconditional_probs":
            run_cmd += " --unconditional_probs_only 1"

        # 模型与采样参数
        run_cmd += f" --model_name {model_name}"
        if use_soluble_model:
            run_cmd += " --use_soluble_model"
        if ca_only:
            run_cmd += " --ca_only"
        run_cmd += f" --num_seq_per_target {num_seq_per_target}"
        run_cmd += f' --sampling_temp "{sampling_temp}"'
        run_cmd += f" --batch_size {batch_size}"
        run_cmd += f" --seed {seed}"
        run_cmd += f" --backbone_noise {backbone_noise}"

        if save_score:
            run_cmd += " --save_score 1"
        if save_probs:
            run_cmd += " --save_probs 1"

        if omit_AAs:
            run_cmd += f' --omit_AAs "{omit_AAs}"'

        # PSSM参数
        if pssm_multi > 0:
            run_cmd += f" --pssm_multi {pssm_multi}"
        if pssm_threshold != 0:
            run_cmd += f" --pssm_threshold {pssm_threshold}"
        if pssm_bias_flag:
            run_cmd += " --pssm_bias_flag 1"
        if pssm_log_odds_flag:
            run_cmd += " --pssm_log_odds_flag 1"

        # 高级JSONL文件
        if bias_AA_jsonl:
            run_cmd += f" --bias_AA_jsonl {self._as_path(bias_AA_jsonl)}"
        if bias_by_res_jsonl:
            run_cmd += f" --bias_by_res_jsonl {self._as_path(bias_by_res_jsonl)}"
        if omit_AA_jsonl_file:
            run_cmd += f" --omit_AA_jsonl {self._as_path(omit_AA_jsonl_file)}"
        if pssm_jsonl_file:
            run_cmd += f" --pssm_jsonl {self._as_path(pssm_jsonl_file)}"

        cmd_parts.append(run_cmd)
        full_cmd = " && ".join(cmd_parts)

        print(f"[ProteinMPNN] 执行命令:\n{full_cmd}")

        # ---------- 5. 执行 ----------
        result = execCmd(full_cmd, cwd=str(mpnn_dir), timeout=3600)
        exitcode = result.returncode
        stdout = result.stdout
        stderr = result.stderr

        print(f"[ProteinMPNN] exitcode={exitcode}, duration={result.duration:.2f}s")
        if stdout:
            print(f"[ProteinMPNN] stdout:\n{stdout}")
        if stderr:
            print(f"[ProteinMPNN] stderr:\n{stderr}")

        if exitcode != 0:
            raise RuntimeError(
                f"ProteinMPNN 子进程返回非零退出码 {exitcode}.\n"
                f"--- stdout ---\n{stdout}\n"
                f"--- stderr ---\n{stderr}"
            )

        # ---------- 6. 收集输出 ----------
        output_zip_path = cwd / "proteinmpnn_outputs.zip"

        # 将所有输出目录打包
        output_subdirs = [
            "seqs",
            "scores",
            "probs",
            "score_only",
            "conditional_probs_only",
            "unconditional_probs_only",
        ]
        files_to_zip = []
        for subdir in output_subdirs:
            subdir_path = output_dir / subdir
            if subdir_path.is_dir():
                for fp in subdir_path.rglob("*"):
                    if fp.is_file():
                        arcname = str(fp.relative_to(output_dir))
                        files_to_zip.append((fp, arcname))

        # 也包含解析后的jsonl
        if parsed_chains.is_file():
            files_to_zip.append((parsed_chains, parsed_chains.name))

        if not files_to_zip:
            raise RuntimeError(
                f"ProteinMPNN 运行成功但未产生任何输出文件。\n"
                f"--- stdout ---\n{stdout}\n"
                f"--- stderr ---\n{stderr}"
            )

        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp, arcname in files_to_zip:
                zf.write(fp, arcname)
        print(f"[ProteinMPNN] 输出已打包: {output_zip_path}")

        # ---------- 7. 生成报告 ----------
        report_path = cwd / "report.md"
        self._write_report(
            report_path,
            True,
            args,
            stdout,
            stderr,
            output_dir,
            str(output_zip_path.relative_to(cwd)),
        )

        return {
            "output_zip": "proteinmpnn_outputs.zip",
            "report": "report.md",
            "success": True,
        }

    def _as_path(self, value):
        """归一化平台上传文件值，兼容字符串、对象和列表。"""
        if not value:
            return Path("")
        if isinstance(value, list):
            if not value:
                raise ValueError("文件列表为空")
            value = value[0]
        if isinstance(value, dict):
            for key in ("path", "file", "url", "value", "name"):
                if value.get(key):
                    value = value[key]
                    break
        if not isinstance(value, (str, os.PathLike)):
            raise TypeError(f"无法识别的文件路径格式: {type(value).__name__}")
        return Path(value).expanduser()

    def _write_report(
        self, report_path, success, args, stdout, stderr, output_dir, output_zip
    ):
        """生成中文报告。"""
        mode_map = {
            "design": "序列生成",
            "score_only": "评分模式",
            "conditional_probs": "条件概率计算",
            "unconditional_probs": "无条件概率计算",
        }
        mode_str = mode_map.get(args.get("mode", "design"), args.get("mode", "design"))

        # 扫描输出文件
        output_files = []
        if output_dir and output_dir.is_dir():
            for subdir in [
                "seqs",
                "scores",
                "probs",
                "score_only",
                "conditional_probs_only",
                "unconditional_probs_only",
            ]:
                subdir_path = output_dir / subdir
                if subdir_path.is_dir():
                    files = [f.name for f in subdir_path.iterdir() if f.is_file()]
                    if files:
                        output_files.append(f"**{subdir}/**: {', '.join(files)}")

        report = f"""# ProteinMPNN 运行报告

## 运行状态
- **状态**: {"成功" if success else "失败"}
- **运行时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 输入参数
| 参数 | 值 |
|------|-----|
| 运行模式 | {mode_str} |
| 模型 | {args.get('model_name', 'v_48_020')} |
| 设计链 | {args.get('chains_to_design', '全部') or '全部'} |
| 采样温度 | {args.get('sampling_temp', '0.1')} |
| 每目标序列数 | {args.get('num_seq_per_target', 1)} |
| 批量大小 | {args.get('batch_size', 1)} |
| 随机种子 | {args.get('seed', 0)} |
| CA-only模式 | {'是' if args.get('ca_only', False) else '否'} |
| 可溶性模型 | {'是' if args.get('use_soluble_model', False) else '否'} |
| 骨架噪声 | {args.get('backbone_noise', 0.0)} |
| 保存分数 | {'是' if args.get('save_score', False) else '否'} |
| 保存概率 | {'是' if args.get('save_probs', False) else '否'} |
| 固定位置 | {args.get('fixed_positions', '无') or '无'} |
| 对称位置 | {args.get('tied_positions', '无') or '无'} |
| 同源寡聚体 | {'是' if args.get('homooligomer', False) else '否'} |
| 省略氨基酸 | {args.get('omit_AAs', 'X')} |
| PSSM multi | {args.get('pssm_multi', 0.0)} |
| PSSM阈值 | {args.get('pssm_threshold', 0.0)} |

## 输出产物
"""
        if output_files:
            report += "\n".join([f"- {f}" for f in output_files])
        else:
            report += "- 无输出文件"

        if output_zip:
            report += f"\n\n- **打包文件**: `{output_zip}`"

        report += f"""

## 日志输出
### 标准输出
```
{stdout[:4000] if stdout else "(无)"}
```

### 标准错误
```
{stderr[:4000] if stderr else "(无)"}
```

## 说明
- `score` 表示被设计残基的平均负对数概率
- `global_score` 表示所有残基的平均负对数概率
- 序列文件中 `/` 分隔不同链的序列
- 如需查看结构可视化，请下载PDB文件到本地查看
"""

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"[ProteinMPNN] 报告已生成: {report_path}")
