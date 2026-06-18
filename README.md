# rootless-pinyin

一个不需要 root 权限的 Linux 拼音输入法。适合学校、实验室、公司服务器这类不能
`sudo`，但系统已经有 `libpinyin` / `libpinyin-data` 的桌面环境。

## 中文

### 安装

直接在终端运行：

```bash
curl -fsSL https://raw.githubusercontent.com/DeTaiDong/rootless-pinyin/main/bootstrap.sh | bash
```

如果没有 `curl`，用 `wget`：

```bash
wget -qO- https://raw.githubusercontent.com/DeTaiDong/rootless-pinyin/main/bootstrap.sh | bash
```

安装脚本会自动下载项目并部署输入法。大多数情况下装完就能直接用；如果设置里还
看不到输入法，注销并重新登录一次。

### 使用

切换输入法：

```text
Super + Space
```

在 GNOME 设置里也可以手动添加：

```text
Settings -> Keyboard -> Input Sources -> + -> Chinese -> Pinyin (libpinyin, no-root)
```

输入方式：

- 输入 `nihao`，按 `Space` 或 `Enter` 上屏。
- 按数字键 `1` 到 `9` 选候选词。
- 轻按 `Shift` 在拼音模式和英文模式之间切换。
- 拼音里可以用 `'` 分隔音节，例如 `xi'an`。
- 中文模式下会自动输出常用中文标点，例如 `，。？！；：`。
- 按 `Backspace` 删除拼音。
- 按 `Esc` 取消输入。

### 更新

```bash
curl -fsSL https://raw.githubusercontent.com/DeTaiDong/rootless-pinyin/main/bootstrap.sh | bash -s -- --update
```

### 卸载

```bash
curl -fsSL https://raw.githubusercontent.com/DeTaiDong/rootless-pinyin/main/bootstrap.sh | bash -s -- --uninstall
```

### 手动安装

如果你想自己 clone：

```bash
git clone https://github.com/DeTaiDong/rootless-pinyin.git
cd rootless-pinyin
./install.sh
```

### 常见问题

如果提示缺少 `libpinyin`、`libpinyin-data`、`python3-gobject` 或 IBus 绑定，
说明系统依赖不完整，需要管理员安装。

如果安装成功但看不到输入法，先试试重新登录。还不行的话检查：

```bash
ibus list-engine | grep pypinyin
ls ~/.local/share/ibus/component/pypinyin.xml
```

如果你的 `libpinyin` 不在常见路径，可以手动指定：

```bash
LIBPINYIN_PATH=/path/to/libpinyin.so \
LIBPINYIN_DATA_DIR=/path/to/libpinyin/data \
./install.sh
```

## English

A rootless Linux pinyin input method backed by the system `libpinyin`. It
installs as a user-level IBus engine, so no `sudo` is required.

Install:

```bash
curl -fsSL https://raw.githubusercontent.com/DeTaiDong/rootless-pinyin/main/bootstrap.sh | bash
```

Use `Super+Space` to switch to **Pinyin (libpinyin, no-root)**. If it does not
appear immediately, log out and log back in once. Tap `Shift` to switch between
pinyin mode and direct English input.

Update:

```bash
curl -fsSL https://raw.githubusercontent.com/DeTaiDong/rootless-pinyin/main/bootstrap.sh | bash -s -- --update
```

Uninstall:

```bash
curl -fsSL https://raw.githubusercontent.com/DeTaiDong/rootless-pinyin/main/bootstrap.sh | bash -s -- --uninstall
```

Manual install:

```bash
git clone https://github.com/DeTaiDong/rootless-pinyin.git
cd rootless-pinyin
./install.sh
```
