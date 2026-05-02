# FloArc

FloArc 是一个 Windows 工具，用来为当前前台窗口生成一个跟随的 Acrylic 模糊遮罩，并按聚焦 / 失焦状态切换窗口透明度。

[English README](README.md)

## Features

- 跟随当前前台窗口的客户区位置与尺寸。
- 为聚焦窗口和失焦窗口分别设置透明度。
- 为聚焦和失焦分别设置不同的透明度过渡时长。
- 默认排除桌面、任务栏、系统托盘弹窗、菜单、下拉框、工具提示等临时窗口。
- 常驻系统托盘，支持 `Restart` 和 `Close`。

## Requirements

- Windows 10 / 11
- Python 3
- `PyYAML`

## Installation

安装依赖：

```powershell
pip install -r requirements.txt
```

直接运行：

```powershell
python main.py
```

首次启动时，如果程序目录下不存在 `config.yaml`，会自动生成默认配置文件。

## Configuration

首次启动自动生成的默认模板如下：

```yaml
windows_opacity:
  focused: 200   # 0 - 255, -1 = disable
  unfocused: 220 # 0 - 255, -1 = disable
  transition_duration:
    focus: 500    # milliseconds, -1 = instant
    unfocus: 500  # milliseconds, -1 = instant

# Blur overlay settings
blur:
  color: "333333"
  opacity: 32    # 0 - 255
  alpha: 220     # 0 - 255
  animate_duration: 500

# Exclusion rules
exclude:
  classes:
    - Progman
    - WorkerW
    - Shell_TrayWnd
    - Shell_SecondaryTrayWnd
    - NotifyIconOverflowWindow
    - "#32768"
    - ComboLBox
    - tooltips_class32
    - Xaml_WindowedPopupClass
    - Windows.UI.Core.CoreWindow
    - ConsoleWindowClass
  titles:
    - "Windhawk"
  executables:
    - "Pixpin.exe"
    - "Flow.Launcher.exe"
```

配置说明：

- `windows_opacity.focused`：聚焦窗口透明度，范围 `0-255`，设为 `-1` 表示不接管聚焦窗口透明度。
- `windows_opacity.unfocused`：失焦窗口透明度，范围 `0-255`，设为 `-1` 表示不接管失焦窗口透明度。
- `windows_opacity.transition_duration.focus`：聚焦时的透明度过渡时长，单位毫秒，设为 `-1` 或 `0` 表示立即切换。
- `windows_opacity.transition_duration.unfocus`：失焦时的透明度过渡时长，单位毫秒，设为 `-1` 或 `0` 表示立即切换。
- `blur.color`：模糊遮罩颜色，使用不带 `#` 的十六进制 RGB 字符串。
- `blur.opacity`：遮罩颜色强度，范围 `0-255`。
- `blur.alpha`：遮罩窗口透明度，范围 `0-255`。
- `blur.animate_duration`：模糊遮罩淡入时长，单位毫秒。
- `exclude.classes`：按窗口类名精确排除。
- `exclude.titles`：按标题子串匹配排除。
- `exclude.executables`：按进程名排除，支持通配符，匹配时不区分大小写。

说明：

- `focused` 和 `unfocused` 都设为 `-1` 时，FloArc 不会修改任何窗口透明度，只保留模糊遮罩效果。
- 旧配置中的默认排除项会在运行时自动合并，不需要手动补齐任务栏、托盘、菜单、下拉框等常见窗口类。
- 排除规则只影响目标窗口选择和透明度接管，不会修改被排除窗口本身。

一个更常见的使用示例：

```yaml
windows_opacity:
  focused: 235
  unfocused: 210
  transition_duration:
    focus: 180
    unfocus: 320

blur:
  color: "2B2B2B"
  opacity: 28
  alpha: 215
  animate_duration: 350

exclude:
  classes:
    - Progman
    - WorkerW
  titles: []
  executables:
    - "msedge.exe"
```

## Tray

程序启动后会驻留系统托盘。

- 右键托盘图标可看到 `Restart` 和 `Close`。
- `Restart` 会以当前启动参数重新启动，并重新读取程序目录下的 `config.yaml`。
- `Close` 会停止跟踪、恢复已接管窗口的透明度，并退出程序。

## Build

安装打包工具：

```powershell
pip install pyinstaller
```

执行打包：

```powershell
pyinstaller FloArc.spec
```

输出文件默认位于：

```text
dist/FloArc.exe
```

当前打包配置有两个和部署相关的行为：

- `FloArc.spec` 中设置了 `runtime_tmpdir='.'`，PyInstaller 的 `_MEIxxxxxx` 临时目录会跟随启动时的当前工作目录。
- 程序启动时会把工作目录切到可执行文件所在目录，并始终从该目录读取 `config.yaml`。

## Notes

- 正常退出时，PyInstaller 会尝试自动删除 `_MEIxxxxxx` 临时目录。
- 如果进程被强制结束，或者仍有句柄占用临时目录，可能出现 `Failed to remove temporary directory: ...`，这时通常在程序完全退出后手动删除即可。
- 少数自绘或特殊分层窗口可能不适合被接管透明度，必要时请加入排除列表。
- 当前逻辑只处理可见、未最小化、未被系统 cloak 的顶层窗口。