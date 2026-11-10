# StartLux-Decision 请求示例说明

本目录下的 JSON 文件都是发给 `POST /v1/systemone` 的请求体。说明依据服务端源码
（`/home/liufeng/projects/StartLux-Decision/startlux_decide/prompt.py`、`pipeline.py`）和官方文档
`/home/liufeng/projects/StartLux-Decision/docs/api.md`。返回示例来自官方文档，不是本机实测结果。

## 共同结构

```json
{
  "state": "证据：要判断的材料",
  "questions": {
    "你起的题目名": {
      "type": "题型",
      "instructions": "问题本身",
      "criteria": "选项或等级（看题型）"
    }
  }
}
```

| 字段 | 含义 |
|---|---|
| `state` | 证据，也就是模型要看的材料。可以是一段文字，也可以是任意 JSON 对象。 |
| `questions` | 要问的问题集合。每个 key（如 `team`、`quality`）是你自己起的名字，返回结果的 `answers` 用同样的名字对应。 |
| `type` | 题型，只有三种：`noul`（是/否）、`choice`（单选）、`score`（等级打分）。 |
| `instructions` | 问题的文字。`choice` 和 `score` 必填；`noul` 不填时默认问 "Which answer fits the evidence?"。 |
| `criteria` | 选项或等级，不同题型写法不同，见下文。 |

这个模型不生成文字。服务端把问题渲染成带字母的选项（A、B、C……），然后读取模型在每个字母上的概率，
所以返回的都是概率。

## 三种题型速查

| 题型 | `criteria` 写法 | 返回字段 |
|---|---|---|
| `noul` | 可省略；或 `{"true": "描述", "false": "描述"}` | `noul`：回答"是"的概率 |
| `choice` | `{选项id: 描述或 null}`，或选项 id 列表 | `choice`、`confidence`、`probabilities`、`none_probability` |
| `score` | 2 到 10 个等级的数组，从低到高 | `score`（期望等级）、`confidence`、`legend`、`probabilities` |

## 逐个文件解释

### 01_noul.json：是/否题

```json
"edge_visible": { "type": "noul", "instructions": "Is at least one road edge clearly visible in this frame?" }
```

- `state`：描述第 0966 帧，左侧路沿清楚，右侧在阴影里看不到。
- `edge_visible`：题目名，自己起的。
- `type: "noul"`：是/否题，不需要 `criteria`。也可以选填 `{"true": "...", "false": "..."}`，给"是"和"否"各加一句说明。
- 返回示例：`{"type": "noul", "noul": 0.93}`，其中 `noul` 是回答"是"的概率。

### 02_choice.json：单选题

```json
"criteria": { "billing": "Payments, charges and refunds", "shipping": "Delivery and tracking", ... }
```

- `state`：客服工单，用户被重复扣款。
- `type: "choice"`：从列出的选项里选一个。
- `criteria`：写成 `{选项id: 选项描述}`。
  - key（如 `billing`）是选项 ID，返回结果里的 `choice` 就是这个值。
  - value 是给模型看的描述。描述可以写 `null`，也可以直接写列表 `["billing", "shipping"]`，这时只显示 ID。
  - 选项按你写的顺序展示。
- 返回字段：
  - `choice`：最可能的选项 ID。
  - `confidence`：置信度，计算公式为 `(p_max − 1/n) / (1 − 1/n)`，截断到 [0, 1]。
  - `probabilities`：每个选项的概率。
  - `none_probability`：默认也会返回，见 04。

### 03_score.json：等级打分题

```json
"criteria": ["0: unusable ...", "1: poor ...", "2: acceptable ...", "3: good ...", "4: excellent ..."]
```

- `type: "score"`：在一个有序的等级尺度上打分。
- `criteria`：一个数组，必须从低到高排，长度 2 到 10。服务端按数组下标给等级编号 0、1、2……。
  字符串开头的 "0:" 只是方便人读，编号不靠它。
  也可以写成 `{数字key: 描述}`，服务端会按数字从小到大排序。
- 返回字段：
  - `score`：期望等级，即按概率加权的平均值。例如 2.3 表示介于 acceptable 和 good 之间。
  - `probabilities`：各级的概率，key 是 `"0"` 到 `"n-1"`。
  - `legend`：等级编号和你写的描述的对照表。
  - `confidence`：概率是否集中在某一级，越接近 1 越集中。

### 04_choice_allow_none.json：允许"都不对"

```json
"allow_none": true
```

- 这张工单讲的是相机崩溃，属于技术问题，但选项里故意没有 technical。
- `allow_none: true`：服务端自动在最后加一个选项 "None of the above"。如果它的概率最高，返回 `"choice": null`。
- 返回里的 `probabilities` 只包含你列出的选项，并重新归一化为和等于 1。`none_probability` 表示"没有合适选项"的程度。
- 和 `none_check` 的区别：
  - `none_check` 默认开启，每道单选题都会返回 `none_probability`，但 `choice` 一定是列出的某个选项。
  - 打开 `allow_none` 后，`choice` 才可能是 `null`。
- 官方建议把 `none_probability >= 0.2` 当作"列出的选项都不合适"。按官方测试，这个阈值能抓出 66.3% 的无正确选项问题，
  误报 2.2%。`decision_client.py` 里的 ⚠️ 提示用的就是这个阈值。
- `none_probability` 适合当报警分数看，它不是严格校准过的概率。
- 不要自己加一个叫 "None of the above" 的选项，否则返回 422 错误。
- `allow_none` 只对 `choice` 有效，`noul` 和 `score` 会忽略它。

返回示例：

```json
"team": {"type": "choice", "choice": null, "confidence": 0.33,
         "probabilities": {"billing": 0.667, "shipping": 0.333}, "none_probability": 0.7}
```

### 05_multi_questions.json：JSON 格式证据 + 一次问多题

- `state` 在这里是一个 JSON 对象，不是字符串。里面的 `frame_id`、`scene`、`annotator`、`lines`、`points`、
  `x_range`、`note` 都是你自己的业务数据，服务端不解析这些字段名，只把整个对象压缩成 JSON 文本给模型看。
  字段名起得清楚，模型就更容易读懂。
- 数组有 8 个及以上元素时，服务端会给每个元素加 `_index`。
- `questions` 里有 5 道题：4 道 `noul` 和 1 道 `score`。每道题独立回答，共用同一份 `state`，返回结果里按各自的 key 分开。

### 06_score_binary.json：用 score 做二分类

- `criteria` 只有两级：`0: reject`、`1: accept`。
- 返回的 `score` 是 0 到 1 之间的值，相当于"接受"的概率。
- 效果和 `noul` 类似，区别是两个选项各有你写的描述。用 `noul` 加
  `"criteria": {"true": "...", "false": "..."}` 也能做到同样的事。

### 07_long_choices.json：超过 26 个选项

- 有 30 个选项（`topic_00` 到 `topic_29`）。字母只有 A 到 Z，模型一次最多读 26 个。
- 超过时服务端自动做淘汰赛：先把选项分成每组不超过 25 个的几组，每组取前 3 名进入决赛，再从决赛里选。
  没进决赛的选项共分 0.001 的概率。
- 写法和普通 `choice` 完全一样，不需要额外参数。`usage.input_tokens` 会更大，因为读了好几轮。

## 可选控制字段

这些字段写在请求顶层，和 `state`、`questions` 同级。

| 字段 | 作用 |
|---|---|
| `allow_none` | 整个请求的默认值，单题里写的会覆盖它。 |
| `none_check` | 默认 `true`，单选题返回 `none_probability`。 |
| `think_mode` / `gate` / `think_budget` / `mix` | 只对 AutoThink 模型有效，控制何时先"思考"。Instant 模型一律单遍回答。 |
| `return_details` / `return_thought` | 返回每题的详细读数、耗时和思考文本。 |
| `images` | base64 图片列表，在 `state` 里用 `<image>` 标记图片的位置。 |

## 返回中的 usage

- `usage.input_tokens`：读入的所有提示词 token 数（淘汰赛的每一轮都算）。
- `usage.output_tokens`：思考生成的 token 数。Instant 模型恒为 0。

## 运行

```bash
cd /home/liufeng/projects/startlux_clients
python decision_client.py --file examples/04_choice_allow_none.json        # 友好格式
python decision_client.py --file examples/04_choice_allow_none.json --raw  # 原始 JSON
```

服务地址默认为 `http://localhost:8095`，可用 `--url` 或环境变量 `STARTLUX_URL` 修改。

## 备注：my_request.json

上级目录的 `my_request.json` 里，`bottom_issue` 题同时有自定义选项 `"none"` 和 `allow_none: true`。
这样不会报错，但两者语义重叠，"没问题"的概率可能会分散到这两个选项上，建议二选一。
