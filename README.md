# rootless-pinyin

不用 `sudo` 也能安装的 Linux 拼音输入法。

适合学校机房、实验室、公司电脑、远程 Linux 桌面等没有 root 权限的环境。前提是系统已经有 `libpinyin` / `libpinyin-data`。

## 快速安装

```bash
curl -fsSL https://raw.githubusercontent.com/DeTaiDong/rootless-pinyin/main/bootstrap.sh | bash
```

没有 `curl` 的话：

```bash
wget -qO- https://raw.githubusercontent.com/DeTaiDong/rootless-pinyin/main/bootstrap.sh | bash
```

安装完成后，用 `Super + Space` 切换到：

```text
Pinyin (libpinyin, no-root)
```

如果设置里暂时看不到，注销并重新登录一次。

## 怎么打字

- `Space` 或 `1`：上屏第一个候选
- `2` 到 `9`：选择其他候选
- `Enter`：上屏原始拼音，例如 `nihao`
- `↓/→`：下一页候选
- `↑/←`：上一页候选
- `Shift`：切换拼音/英文模式
- `'`：分隔拼音，例如 `xi'an`
- `Esc`：取消输入

## 设置

打开图形设置窗口：

```bash
rootless-pinyin-config
```

如果命令找不到：

```bash
~/.local/bin/rootless-pinyin-config
```

设置窗口可以调整：

- 模糊音
- 中文标点
- Shift 中英切换
- 候选数量
- 自定义短语
- 设置窗口/悬浮框主题

配置保存后，切换一下输入法，或者运行更新命令刷新 IBus。

## 自定义短语

图形设置里可以添加短语，例如：

```text
email -> your.name@example.com
xiexie -> 谢谢
```

也可以用命令：

```bash
rootless-pinyin-config --cli phrase add email your.name@example.com
rootless-pinyin-config --cli phrase remove email
```

## 可选悬浮框

```bash
rootless-pinyin-panel
```

它会显示一个小窗口，点击“设置”可以打开配置页。这个功能默认不会自启动。

## 更新

```bash
curl -fsSL https://raw.githubusercontent.com/DeTaiDong/rootless-pinyin/main/bootstrap.sh | bash -s -- --update
```

## 卸载

```bash
curl -fsSL https://raw.githubusercontent.com/DeTaiDong/rootless-pinyin/main/bootstrap.sh | bash -s -- --uninstall
```

## 手动安装

```bash
git clone https://github.com/DeTaiDong/rootless-pinyin.git
cd rootless-pinyin
./install.sh
```

## 常见问题

如果提示缺少 `libpinyin`、`libpinyin-data`、`python3-gobject` 或 IBus 绑定，说明系统依赖不完整，需要管理员安装。

如果安装成功但看不到输入法：

```bash
ibus list-engine | grep pypinyin
ls ~/.local/share/ibus/component/pypinyin.xml
```

如果 `libpinyin` 不在常见路径：

```bash
LIBPINYIN_PATH=/path/to/libpinyin.so \
LIBPINYIN_DATA_DIR=/path/to/libpinyin/data \
./install.sh
```

## English

Rootless pinyin input method for Linux desktops. No `sudo` required.

Install:

```bash
curl -fsSL https://raw.githubusercontent.com/DeTaiDong/rootless-pinyin/main/bootstrap.sh | bash
```

Use `Super + Space` to switch to **Pinyin (libpinyin, no-root)**.

Settings:

```bash
rootless-pinyin-config
```

Update:

```bash
curl -fsSL https://raw.githubusercontent.com/DeTaiDong/rootless-pinyin/main/bootstrap.sh | bash -s -- --update
```

Uninstall:

```bash
curl -fsSL https://raw.githubusercontent.com/DeTaiDong/rootless-pinyin/main/bootstrap.sh | bash -s -- --uninstall
```
