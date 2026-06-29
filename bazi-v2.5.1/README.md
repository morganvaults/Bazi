# bazi-v2

Codex skill for Bazi/八字 charting, four-pillar structure analysis, scoring, luck pillars, annual luck, and practical interpretation.

> **Tip:** For more accurate luck pillar (大运) calculation, use the `--wenzhen` flag to cross-check via the Wenzhen (问真) public API. This is especially useful when only the four pillars are known without a confirmed birth time. Internet connection required.

## Chart Reading Logic

The skill follows a tiered approach based on available data:

- **S-tier** (full data): Complete birth date, time, gender, and location. Enables full charting, luck pillars, annual luck, and scoring.
- **A-tier**: Birth date, hour, and gender. Standard charting with local standard time; true solar time not applied.
- **B-tier**: Four pillars only. Performs local structural analysis. Use `--wenzhen --pillars` to reverse-lookup candidate birth times, then confirm with `--candidate-index` for precise luck pillar calibration.
- **C-tier**: No data. Prompt user for birth information before proceeding.

### Core Calculation Steps

1. **Calendar & month branch** — Year pillar boundary is Start of Spring (立春), not Lunar New Year. Month branches follow the 12 solar terms.
2. **Five elements** — Both simple and weighted counts. Weights: heavenly stem 1.0; earthly branch main qi 1.0, mid qi 0.6, residual qi 0.3; month branch extra-weighted.
3. **Day master strength** — Based on month branch, roots, stems, and interactions (combinations, clashes, harms).
4. **Useful god (用神)** — Three layers: suppression/support god, seasonal adjustment god, and mediation god.
5. **Luck pillars (大运)** — Yang male / Yin female go forward; Yin male / Yang female go backward. 3 days = 1 year, 1 day = 4 months.
6. **Scoring** — Chart structure score and domain scores (career, wealth, relationships) computed separately from annual luck activation score.
7. **Tomb, void, and 12 growth stages** — Granular analysis; not every 辰戌丑未 branch is treated as day master burial.
8. **Combinations, purity, and annual interactions** — Combination success evaluated against seasonal support, stems, roots, and clash conditions.

### Output Modes

| Flag | Description |
|------|-------------|
| *(default)* | `summary` — quick daily reading |
| `--detail standard` | More detail without full verbose output |
| `--detail full` | Complete technical analysis |
| `--json` | Machine-readable JSON |
| `--score-only` | Scores only |
| `--wenzhen` | Cross-check via Wenzhen API (requires internet) |
| `--liu-nian` / `--yun-years` | Annual luck and luck-pillar interaction analysis |

## Skill Files

- `SKILL.md`: agent-facing usage guide.
- `references/methodology.md`: calculation and interpretation methodology.
- `scripts/bazi.py`: primary CLI entrypoint.
- `V2_UPDATE_NOTES.md`: release notes.

---

# 八字技能说明（中文）

> **提示：** 如果可以联网，推荐使用 `--wenzhen` 参数调用问真八字公开 API 辅助排大运，精度更高。尤其适合只知道四柱、不确定具体出生时间的情况。

## 看盘逻辑

技能按资料完整度分四级处理：

- **S 级**：公历出生日期、时辰、性别、出生地齐全，可做完整排盘、大运、流年、评分。
- **A 级**：有公历日期、小时、性别，做标准排盘，默认本地标准时，不启用真太阳时。
- **B 级**：只给四柱八字，先做本地结构分析。若需要精确大运，用 `--wenzhen --pillars` 反查候选生日，再用 `--candidate-index` 校准起运和大运。
- **C 级**：无资料，先索取出生信息。

### 核心计算步骤

1. **历法与月令** — 年柱以立春为界，月柱以十二节气为界，不以农历正月初一为界。
2. **五行统计** — 同时输出简单五行和加权五行（天干 1.0，地支藏干主气 1.0 / 中气 0.6 / 余气 0.3，月令额外加权）。
3. **日主强弱** — 看月令、通根、透干、生扶克泄耗以及合冲刑害。
4. **用神喜忌** — 三层取用：扶抑用神 → 调候用神 → 通关用神。
5. **大运** — 阳男阴女顺排，阴男阳女逆排；三天一岁，一天四个月。
6. **评分** — 原局结构分与领域评分（事业财运婚恋）分开，运势兑现评分单独呈现。
7. **墓库、空亡、十二长生** — 分层细判，不把所有辰戌丑未都作日主入墓。
8. **合化清浊与运年交互** — 合化成败看化神是否得令、透干、有根；格局清浊看月令格神与混杂情况。

### 输出模式

| 参数 | 说明 |
|------|------|
| （默认） | `summary` 简版，日常快速看盘 |
| `--detail standard` | 比默认略详细 |
| `--detail full` | 完整技术排盘 |
| `--json` | JSON 格式输出 |
| `--score-only` | 仅输出评分 |
| `--wenzhen` | 联网调用问真 API 校准（**推荐用于大运精度要求高时**） |
| `--liu-nian` / `--yun-years` | 流年与大运交互分析 |

