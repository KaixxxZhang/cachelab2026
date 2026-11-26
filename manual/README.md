# Part B 分析手册

给 CacheLab 2026 Part B 用的中文分析手册。读完后自己写报告里的三个 case，手册不代替报告正文。

编译（在本目录）：

```bash
xelatex -interaction=nonstopmode partb-manual.tex
xelatex -interaction=nonstopmode partb-manual.tex
```

需要 `xelatex` 和 `ctex`（`fontset=fandol`）。PDF 是 `partb-manual.pdf`。

重跑全部块形实测（在仓库根目录，会重写 `generated/sweep_case*.tex` 和 `data/`）：

```bash
python3 manual/scripts/analyze_partb.py --crosscheck
```

`--crosscheck` 在 `/tmp` 里用实验框架编译若干非实现块形，不修改仓库里的 `gemm.cpp`。
