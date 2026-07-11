# VoiceOutput Plugin - 语音输出插件

拦截 LLM 回复内容，通过云智 API 的 TTS 接口转换成语音，并发送语音链接。

## 功能

- **自动语音转换**：LLM 回复后自动将文本转为语音，发送语音链接
- **手动语音命令**：通过 `/voice <文本>` 或 `!voice <文本>` 命令手动生成语音
- **文本长度限制**：可配置最大文本长度，避免过长文本占用资源
- **开关控制**：可在插件设置中开启/关闭自动语音功能

## 配置

在插件设置中配置以下参数：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `api_token` | string | 是 | 云智 API 的 Token，从 https://yunzhiapi.cn 获取 |
| `max_text_length` | number | 否 | 最大文本长度，默认 500 字符 |
| `auto_voice` | boolean | 否 | 是否自动语音输出，默认开启 |

## 使用方法

### 自动模式
启用 `auto_voice` 后，LLM 的回复会自动转为语音，并发送语音链接。

### 手动命令
```
/voice 你好，欢迎使用语音插件
!voice 今天天气真不错
.voice Hello, welcome to voice plugin
/语音 这是一条语音消息
```

## API 说明

使用 [云智 API](https://yunzhiapi.cn) 的语音合成接口：
- 接口地址：`https://yunzhiapi.cn/API/saiyysc.php`
- 请求方式：GET/POST
- 返回格式：JSON（默认）/ WAV

## 文件结构

```
VoiceOutputPlugin/
├── main.py                          # 插件主类
├── manifest.yaml                    # 插件清单
├── requirements.txt                 # 依赖
├── .env.example                     # 环境变量示例
├── README.md                        # 说明文档
├── assets/
│   └── icon.svg                     # 插件图标
├── components/
│   └── event_listener/
│       ├── default.py               # 事件监听器
│       └── default.yaml             # 监听器配置
├── core/
│   └── tts.py                       # TTS API 调用逻辑
└── data/