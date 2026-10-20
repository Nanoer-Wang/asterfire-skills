# 普通项目迁移为 Kit

仅处理迁移决策；输入、输出、Demo、报告、元数据和打包统一遵守同目录 `kit-development-rules.md` 及 Kit 主入口。实际镜像准备与发布使用 `../../asterfire-platform-devops/SKILL.md`。

先运行 `scripts/porting_analyzer.py` 提取入口、依赖、外部命令和参数。扫描结果是线索，不能替代运行分析或平台 SIF 可用性核验。

## 普通项目分析清单

查看项目时必须记录：

1. 项目根目录结构。
2. Python 文件列表。
3. 是否已有 `class runner(Tool)`。
4. 是否已有 `config/input.json`、`config/configure.json`、`config/long_description.md`。
5. 是否已有 `Makefile`。
6. 可能的普通入口文件：`main.py`、`app.py`、`cli.py`、`run.py`、`predict.py`、`train.py`、带 `if __name__ == "__main__"` 的脚本。
7. 命令行参数：`argparse`、`click`、`typer`。
8. 第三方 Python 依赖。
9. 外部二进制命令。
10. 真实输入文件、文本参数和可选参数。
11. 真实输出文件和目录。
12. 项目运行时是否写入固定路径或绝对路径。
13. 运行是否依赖当前工作目录。

## 入口选择规则

### 已经是 Kit

如果已有 `class runner(Tool)`：

- 定位包含该类的文件。
- 检查是否有 `DISPLAY_NAME`、`NETWORK`、`CPU`、`GPU`、`SIF`。
- 若缺 `SIF` 或 `SIF` 是占位，必须先确认 SIF。
- 不要新建第二个 `runner` 类。

### 普通项目

如果没有 `class runner(Tool)`：

- 如果有清晰命令行入口，优先新建平台入口文件包装该命令。
- 如果有清晰函数入口，优先新建平台入口文件导入并调用该函数。
- 如果顶层代码复杂，先拆出业务函数到 `utils/`，再让 `runner.call()` 调用。

不要假设入口文件一定叫 `main.py`。

## 适配方式

### 函数调用式

适合原项目已经有函数：

```python
def run(input_file, output_dir, threshold=0.5):
    ...
```

平台入口负责：

- 从 `kwargs['args']` 取参数。
- 检查输入存在。
- 创建当前工作目录下的输出路径。
- 调用原函数。
- 检查输出是否存在。
- 写专业中文 report.md，展示关键结果和可视化，不直接展开运行日志。
- return dict。

### 命令行包装式

适合原项目已经稳定支持 CLI：

```bash
python predict.py --input xxx.csv --output result.csv
```

平台入口中使用：

```python
completed = subprocess.run(command, cwd=str(cwd), text=True, capture_output=True, check=False)
```

必须打印或记录：

- command
- returncode
- 输出文件路径
- 文件是否存在
- 详细命令输出和错误信息写入 `run.log`、`stdout.log`、`stderr.log` 等文件

注意：`report.md` 不直接展示 stdout/stderr 全文，只在“如何查看结果”中说明日志文件位置。

### 拆分 utils 式

如果原项目是顶层脚本，把业务逻辑拆成：

```text
utils/project_core.py
```

入口文件只保留平台适配层，不把大量业务代码堆在 `runner.call()` 里。



## 原项目案例与交付

扫描 README、docs、examples、tests、tutorials 和 notebooks，将官方典型命令转成最小表单及真实 Demo；每种主要模式尽量有轻量用例。文件放 demos 并以相对文件名引用，不能把大权重当 Demo 打包。只有运行依赖需要镜像，业务脚本保留在 Kit，版本/提交记录在交付中。

迁移后对照原命令检查参数默认值、单位、输出语义和错误码；本地验证通过后，按用户要求由 DevOps 发布并用最小真实案例检查结果。用户只要代码/ZIP时到该范围结束。
