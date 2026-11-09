# word-history —《World History Timeline · Decade by Decade》结构化数据集

[![ci](https://github.com/shalom-lab/world-history/actions/workflows/ci.yml/badge.svg)](https://github.com/shalom-lab/world-history/actions/workflows/ci.yml)
[![pages](https://github.com/shalom-lab/world-history/actions/workflows/pages.yml/badge.svg)](https://shalom-lab.github.io/world-history/)

把 SenseForMaps 的巨幅世界史时间线海报（`source.jpg`，2048×2048）整理成可查询、可复用的结构化数据。

**当前版本**：140 条横带、1850 个色块（时间段）、10 个大区、98 个图例色块、348 条中英对照字符串。
**覆盖度**：**60/60 转写切片全部完成**，15 个横向分带全部完整。图面解析覆盖 100%。

```
word-history/
├─ source.jpg                        原始位图（只读副本，1.2 MB）
├─ data/                             结构化数据（主产物）
│  ├─ meta.json                      来源、坐标系、标定、统计、覆盖度、局限
│  ├─ sections.json                  10 个大区（SOUTHERN AFRICA…）及其 y 区间
│  ├─ entities.json                  140 条横带 = 140 个实体
│  ├─ spans.json                     1850 个色块 = 时间段（含起止年份）
│  ├─ legend.json                    22 个语系 / 98 个色块，含采样 RGB
│  ├─ columns.json                   像素 ↔ 年份换算
│  └─ timeline.csv                   长表（Excel / BI 直接用）
├─ schema/                           meta / section / entity / span / legend 的 JSON Schema
├─ dist/world-history-timeline.xlsx  7 个工作表（含 Coverage 覆盖度表）
├─ viewer/index.html                 交互总览：按鼠标位置缩放、拖拽平移、语系过滤
├─ build/                            可重跑的抽取流水线
│  ├─ tiler.py / make_tiles.py       切片 + 坐标尺
│  ├─ segment.py                     行内色块游程提取
│  ├─ merge.py / refine.py           合并标注、用像素重算边界
│  ├─ build_dataset.py               生成 data/*
│  ├─ validate.py                    一致性校验（含 schema 校验）
│  ├─ schema_check.py                轻量 JSON-Schema 校验器（环境无 jsonschema）
│  ├─ make_xlsx.py / make_viewer.py  出 Excel / 出 HTML
│  ├─ test_viewer.js                用 stub DOM 跑一遍 viewer 的 JS（本机无浏览器）
│  └─ labels/*.json                  53 个切片的逐块人工识读结果（一手证据）
```

## 1. 这张图怎么读

海报是一张「行 × 时间」矩阵：

* **横轴**：刻度线每 100 年一条，标签 `-3100 … -100, 1, 100 … 2000`（负数 = 公元前）。
  每 10 年一列 = **3.808 px**，这正是标题 "decade by decade" 的含义。
* **纵轴**：每 5–20 px 一条横带，一条带 = 一个民族/文化/政权/殖民地的"轨道"。
* 横带内的**色块**＝该实体在某个时段存在；块内常印名称（王朝、帝国、文化期）。
* 色块颜色编码**语系**（图例 box "Civilizations by language"）。
* 左栏竖排文字＝大区（SOUTHERN AFRICA、NORTHERN AFRICA、EUROPE…）。

所以数据模型是：**实体（横带）= 轨道，色块（span）= 这条轨道上依次出现的政权/文化**。
一条带在几千年里可以换很多个"住户"，这正是海报的表达方式。

## 2. 抽取方法

1. **轴标定**：在 y=62–74 的轴标签带里检测到 51 个文字块，中心按 38.15 px 等距，
   与贯穿全图的 38.08 px 网格线一致，且标签右对齐于其网格线
   ⇒ `year(x) = −3100 + (x − 60) × 100 / 38.08`。单像素 ≈ 2.6 年，输出统一按 10 年取整。
2. **分块识读**：海报切成 15×4 = 60 块（每块 ~500×130 px，放大 3–3.5 倍），
   渲染时叠加**原图像素坐标尺**，逐块录入「行 y 范围 + 行名 + 色块 x 范围 + 块内文字」，
   存进 `build/labels/`。
3. **像素复算**：转写只给行位置和文字；每个色块的精确边界由 `build/segment.py`
   在原图上按列取中位色、找色变点重算，再把行边界吸附到真实的横向色变线。
   这样年代精度不受目测误差影响。
4. **合并**：列向重叠 30 px 按覆盖率消解；行向跨带边界按「标签 + 几何相接」缝合；
   行区间强制单调不重叠；标签投票用确定性排序（不同 `PYTHONHASHSEED` 结果一致）。
5. **配色归类**：把每个色块的采样色与图例 98 个色块做 RGB 最近邻匹配
   （≤18 = high，≤32 = medium，≤46 且饱和度 ≥0.25 = low，否则留空）。
   实测有效：`#b5fd6d`→Germanic/North，`#fa1672`→Turkic/Chagatai，`#f09090`→Egyptian。

## 3. 数据字典

### entities.json（每条横带）

| 字段 | 含义 |
|---|---|
| `id` | `E001` 起 |
| `order` | 海报自上而下顺序 |
| `name` | 行名（保留海报原拼写，含其自身拼写错误） |
| `section` / `section_name` | 所属大区 |
| `category` | 由名称关键词推断：`state` / `hunter-gatherer` / `farmer` / `pastoralist` / `archaeological culture` / `chiefdom` / `people` / `other` |
| `language_family` | 该带色块中出现最多的语系 |
| `y0`,`y1` | 原图像素纵坐标 |
| `start_year`,`end_year` | 该带所有色块的包络 |
| `label_confidence` | 行名转写置信度 high / medium / low |
| `name_source` | `row-label`（行本身有标题）或 `span-text`（退化到色块文字） |
| `occluded_by_legend` | 该行是否被图例贴纸遮住 |

### spans.json（每个色块）

| 字段 | 含义 |
|---|---|
| `start_year` / `end_year` | 负数 = 公元前；按 10 年取整 |
| `label` | 色块内印刷文字（可能为空） |
| `color_hex` / `fill_class` | 原图采样得到的填充色与其色相归类 |
| `language_family` / `_alt` | 最近 / 次近图例色块所属语系 |
| `color_confidence` | high / medium / low / none（匹配质量） |
| `x0`,`x1` | 像素边界，可回溯原图核对 |

## 3.5 viewer 怎么用

`viewer/index.html` 双击即可打开（单文件，数据内联，不需要服务器）：

| 操作 | 效果 |
|---|---|
| 滚轮 | **以鼠标所在年份为锚点**缩放时间轴（指针下的年份不动） |
| Shift + 滚轮 | 缩放行高（时间轴不动），便于看清 5 px 高的细行 |
| 拖拽 | 平移；双击放大 2 倍 |
| 顶部按钮 | 放大 / 缩小 / 重置 / 全览 |
| 语系 chip | 点一下隐藏该语系，再点恢复（名称随语言切换） |
| **搜索框** | 搜行名、语系名，也搜**每个色块里的文字**（中英都搜）；命中行高亮，回车跳到下一处 |
| **左栏滚动条** | 左栏可以单独滚动，和右侧图表双向同步；滚到底就停，不会多出空白 |
| **导出图片** | 把当前视图存成 PNG |
| **导出 CSV** | 导出全部 1850 条时间段（UTF-8 BOM，Excel 直接打开；列名和内容跟随当前语言） |

渲染用 **canvas**，不是 SVG：每帧只画当前视口内的行（约 150–300 个色块），
所以滚轮缩放不会卡。早先的 SVG 版本要重建 1900 个节点，放大时明显掉帧。
文字大小恒定，年代刻度随缩放自动在 1000/500/200/100/50/10 年之间切换；
左栏行名超宽时截断加省略号，不会压到右侧的语系标签。

## 3.6 中英双语（i18n）

**英文是原文，中文是译写**。海报上只印了英文；中文按「英文原文 → 中文」的键值对存在
`data/i18n/zh-CN.json` 里，一个字符串只翻一次：

| 文件 | 作用 |
|---|---|
| `data/i18n/zh-CN.json` | `ui`（界面文案）+ `strings`（348 条标签译文）+ `families`（22 个语系名） |
| `data/entities.json` → `name_zh` | 由 `strings` 解析而来，缺失则回落英文 |
| `data/spans.json` → `label_zh` | 同上 |
| `data/meta.json` → `i18n` | 已装载的 locale、`zh_missing`（缺失清单，本版为 0） |
| `dist/world-history-timeline.xlsx` | Entities / Spans 两个表里 en、zh **并排**成列 |
| `viewer/index.html` | 右上角「中文 / EN」开关，切换行名、块内文字、年代格式与提示 |

为什么翻译不直接写在 Excel 里：同一个字符串会在图上重复出现（`ROMAN EMPIRE` 出现 11 次、
`SPAN` 3 次），写在表里要改 11 处；放在 JSON 字典里改 1 处，所有出现同步，还能做
「缺失检测」（`meta.i18n.zh_missing`）和版本 diff。**Excel 是导出物，不是翻译的主存储。**

**加一种语言**：复制 `data/i18n/zh-CN.json` 为 `xx-XX.json`，补上 `ui` 与 `strings`，
然后在 `build/build_dataset.py` 里把 `zh-CN` 换成新 locale（或改成循环），重跑管线即可。

## 4. 精度与已知局限（先读这段）

* **分辨率是硬上限**。原海报是高清/矢量输出，这张 2048 px 位图把正文压到 5–7 px。
  结果是：**行名与大字块（帝国、王朝、文化期）可靠，细密小字大量不可辨**。
  1850 个色块里只有 446 个（24%）带印刷文字，其余是纯色块——不是漏抓，是原图看不清。
* **时间精度** ±10 年（十年栅格），色块边界对齐到年代列。
* **中亚/东亚的马赛克带（y≈1100–1360）精度更差**：那里的行只有 3–8 px 高，而且一个色块
  常常跨好几行（例如整块紫色同时覆盖宋、元、明、清），所以行的归属和年代边界可能偏
  100–200 年。这些行里的色块 `confidence` 一律标 `low`，请以原图为准。
* **语系配色**有天然歧义：同一色相下 German/Koreanic、Indo-Aryan/Nilo-Saharan、
  Romance/Dravidian 都是近色。`language_family_alt` 给了次近候选，`color_confidence`
  标明可信度；`none` 表示该项没把握。
* **行缝合**：跨切块边界的横带按「同名 + 相接」合并，少数可能被拆成两条或误并。
  `entities.json` 的 `y0/y1` 可直接回原图复核。
* **行名取自各列标签的多数投票**：同一条带在左栏可能叫 “Bantu-speaking herders and farmers”，
  在右栏叫 “KINGDOM OF KONGO”，数据里保存的是票数最高的那个；纯 `[?]` 的占位标签不参与投票。
  逐块原始文字都在 `build/labels/*.json` 里可查。
* **右侧 3–5 px 的国名条**（HONDURAS、BOLIVIA…）只能部分辨读，`conf` 标为 low 的段表示
  仅识别出其中几个词。
* **没有用任何外部史料补**。海报上没印的，数据里就没有；也没有调用网络检索。

## 5. 复现

```bash
pip install pillow numpy openpyxl

python build/make_tiles.py      # 60 张带坐标尺的切片 → build/tiles/
python build/merge.py           # 合并 build/labels/*.json → build/merged_rows.json
python build/refine.py          # 像素重算色块边界 → build/refined.json
python build/build_dataset.py   # → data/*
python build/validate.py        # 一致性 + schema 校验 → build/validation_report.md
python build/make_xlsx.py       # → dist/world-history-timeline.xlsx
python build/make_viewer.py     # → viewer/index.html
```

`build/labels/` 是人工识读的中间层（60 个切片各一份）：改其中任何一处文字或 y 范围，
重跑上面流程就会流到 `data/`、Excel 和 viewer。

**整个流水线是可复现的**：从 `source.jpg` + `build/labels/` 重跑，`data/`、`viewer/`、
`dist/` 与仓库中的版本逐字节一致（xlsx 的 zip 时间戳和 `docProps` 已固定）。
CI 就是靠这条性质做守卫的。

## 6. CI / 部署

| workflow | 触发 | 做什么 |
|---|---|---|
| `.github/workflows/ci.yml` | push / PR | 从 `source.jpg` 重建切片 → 合并 → 精修 → 生成数据 → `validate` + `schema_check` + `acceptance`，最后 `git diff --exit-code`：**仓库里的 `data/`、`viewer/`、`dist/`、`schema/` 必须和干净重建的结果一致**，否则 CI 失败 |
| `.github/workflows/pages.yml` | push 到 main | 同一套构建，然后把 `viewer/index.html` + `data/` + Excel 组装成站点，发布到 GitHub Pages |

站点地址：<https://shalom-lab.github.io/world-history/>（首次需要在
**Settings → Pages → Build and deployment → Source** 选 **GitHub Actions**）。

`build/tiles/`（约 50 MB 切片）不进仓库，由 CI 用 `make_tiles.py` 现场重建。

## 7. 出处

* 图表：SenseForMaps, *World History Timeline – Decade by Decade*。
* 本数据集是对该图的**结构化转录**，不含外部史料补充；引用时请同时标注原图作者。
