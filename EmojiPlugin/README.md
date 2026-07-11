# EmojiPlugin - 表情融合插件

通过云智 API 将两个 Emoji 表情融合为一个，自动发送融合后的表情图片。

## 功能

- **自动融合**：发送包含两个 emoji 表情的消息即可自动触发融合，无需命令前缀
- **图片发送**：融合成功后直接发送图片，简洁无多余文字
- **命令支持**：同时支持 `/emoji <表情1> <表情2>` 命令方式
- **链接可选**：可在配置中开启发送融合结果链接

## 配置

在插件设置中配置以下参数：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `api_token` | string | 是 | 云智 API 的 Token，从 https://yunzhiapi.cn 获取 |
| `show_link` | boolean | 否 | 是否附带发送融合结果链接，默认关闭 |

## 使用方法

### 自动触发
直接发送两个 emoji 表情即可，无需任何命令前缀：
```
😀 😂
🐱 🐶
😎 🥳
```
机器人将自动回复融合后的表情图片。

### 命令方式
```
/emoji 😀 😂
!emoji 🐱 🐶
/表情 😀 😂
/融合 🐱 🐶
```

## API 说明

使用 [云智 API](https://yunzhiapi.cn) 的表情融合接口：
- 接口地址：`https://yunzhiapi.cn/API/emoji/`
- 请求方式：GET/POST
- 返回格式：JSON
- 请求参数：
  - `token`: API 密钥（必填）
  - `go`: 第一个 Emoji 表情（必填）
  - `to`: 第二个 Emoji 表情（必填）
- 返回示例：
```json
{
    "code": 1,
    "text": "获取成功",
    "data": {
        "url": "https://www.gstatic.com/android/keyboard/emojikitchen/20211115/u1f436/u1f436_u1f602.png"
    }
}
```

## 文件结构

```
EmojiPlugin/
├── main.py                          # 插件主类
├── manifest.yaml                    # 插件清单
├── requirements.txt                 # 依赖
├── README.md                        # 说明文档
├── assets/
│   └── icon.svg                     # 插件图标
├── components/
│   ├── commands/
│   │   ├── emoji.py                 # 表情融合命令
│   │   └── emoji.yaml               # 命令配置
│   └── event_listener/
│       ├── default.py               # 事件监听器
│       └── default.yaml             # 监听器配置
├── core/
│   └── emoji.py                     # Emoji API 调用逻辑
└── data/
```