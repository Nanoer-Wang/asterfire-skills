# Runner 路径风险扫描
Runner: /mnt/data/ProteinMPNN.py

## Findings
- line 37: [cwd_relative_risk] cwd = Path.cwd()
- line 84: [cwd_relative_risk] work_dir = cwd / "proteinmpnn_work"
- line 94: [cwd_relative_risk] mpnn_dir = cwd / "ProteinMPNN-main"
- line 108: [python_script_call] helper_scripts/parse_multiple_chains.py
- line 119: [python_script_call] helper_scripts/assign_fixed_chains.py
- line 129: [python_script_call] helper_scripts/make_fixed_positions_dict.py
- line 142: [python_script_call] helper_scripts/make_tied_positions_dict.py
- line 151: [python_script_call] helper_scripts/make_tied_positions_dict.py
- line 159: [python_script_call] protein_mpnn_run.py
- line 248: [cwd_relative_risk] output_zip_path = cwd / "proteinmpnn_outputs.zip"
- line 285: [cwd_relative_risk] report_path = cwd / "report.md"
- line 229: [exec_cwd] str(mpnn_dir

## Recommendations
- 发现 Path.cwd()/cwd 相对路径风险：确认这些路径是否属于运行时工作目录；镜像内置项目不能用 cwd 查找。
- 发现 python xxx.py 调用：若脚本来自镜像内项目，应设置 execCmd cwd 为镜像项目根目录，或改成绝对脚本路径。
