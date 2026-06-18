# rootless-pinyin

一个不需要 root 权限的 Linux 拼音输入法。它用 Python 写成，通过
`ctypes` 直接调用系统自带的 `libpinyin.so`，然后把自己注册成用户级
IBus 输入引擎，安装位置都在 `~/.local/share` 和 `~/.config` 下面。

这个项目主要适合这样的环境：你在学校、实验室、公司或服务器桌面上没有
`sudo` 权限，但系统已经装好了 `libpinyin` / `libpinyin-data`，只是没有
安装完整的 `ibus-libpinyin` 输入法包。

## 中文说明

### 适用场景

- 你使用的是 GNOME 或其他支持 IBus 的 Linux 桌面。
- 你没有 root 权限，不能自己安装系统 RPM/DEB 包。
- 机器上已经有 `libpinyin` 和词库数据。
- 你只需要一个轻量可用的拼音输入法，不追求完整 `ibus-libpinyin` 的所有设置界面。

### 安装前检查

先确认系统里有没有 `libpinyin`：

```bash
rpm -qa | grep libpinyin
```

在 RHEL、Rocky、CentOS 这类系统上，如果能看到类似 `libpinyin`、
`libpinyin-data` 的包名，通常就可以继续。

如果系统不是 RPM 系发行版，也可以检查常见文件是否存在：

```bash
ls /usr/lib64/libpinyin.so.13
ls /usr/lib64/libpinyin/data
```

安装脚本会自动尝试几个常见路径。如果你的系统把 libpinyin 放在特殊位置，
可以安装时手动指定：

```bash
LIBPINYIN_PATH=/path/to/libpinyin.so \
LIBPINYIN_DATA_DIR=/path/to/libpinyin/data \
./install.sh
```

再确认 Python 能导入 IBus 的 GObject Introspection 绑定：

```bash
python3 -c "import gi; gi.require_version('IBus','1.0'); from gi.repository import IBus"
```

这条命令没有输出、没有报错就是正常。如果报错，说明系统缺少
`python3-gobject` 或 IBus typelib，这部分通常需要管理员安装。

### 安装步骤

克隆项目：

```bash
git clone https://github.com/DeTaiDong/rootless-pinyin.git
cd rootless-pinyin
```

运行安装脚本：

```bash
./install.sh
```

安装脚本会做这些事：

- 把 `engine.py` 和 `pinyin_lib.py` 复制到
  `~/.local/share/ibus-pypinyin/`
- 生成 IBus component 文件：
  `~/.local/share/ibus/component/pypinyin.xml`
- 写入 `~/.config/environment.d/ibus-pypinyin.conf`，让下次登录时
  IBus 能找到用户目录下的 component
- 在用户级 D-Bus service 里给 `ibus-daemon` 加上 `--cache=refresh`，
  避免 IBus 继续使用旧的组件缓存
- 如果你已经有自己的用户级 IBus D-Bus service，脚本会先备份成
  `org.freedesktop.IBus.service.pre-pypinyin`
- 在 GNOME 环境下，自动把 `('ibus', 'pypinyin')` 加到输入源列表里

安装完成后，必须注销并重新登录一次。只重启终端通常不够，因为
`ibus-daemon` 和当前 session 的 D-Bus broker 都会缓存启动时看到的输入法组件。

### 启用和使用

重新登录后，打开：

```text
Settings -> Keyboard -> Input Sources
```

正常情况下应该已经能看到：

```text
Pinyin (libpinyin, no-root)
```

如果没有自动出现，可以手动添加：

```text
+ -> Chinese -> Pinyin (libpinyin, no-root)
```

切换输入法可以用 GNOME 默认快捷键：

```text
Super + Space
```

基本用法：

- 输入 `nihao`，按 `Space` 或 `Enter` 上屏最佳候选。
- 按数字键 `1` 到 `9` 选择候选词。
- 按 `Backspace` 删除拼音。
- 按 `Esc` 取消当前输入。

例如输入：

```text
woshizhongguoren
```

可以得到类似：

```text
我是中国人
```

### 卸载

在项目目录里运行：

```bash
./uninstall.sh
```

卸载脚本会删除用户目录里的输入法文件、环境变量文件和 pypinyin 的 D-Bus
覆盖配置。如果安装时备份过你原来的用户级 D-Bus service，也会自动恢复。

卸载后同样建议注销并重新登录一次，让 IBus 和 session bus 刷新状态。

### 常见问题

`ibus engine pypinyin` 提示找不到输入法：

先注销并重新登录。如果还是不行，确认这个文件存在：

```bash
ls ~/.local/share/ibus/component/pypinyin.xml
```

输入时没有候选词：

检查 engine 是否存在且可执行：

```bash
ls -l ~/.local/share/ibus-pypinyin/engine.py
```

再检查 Python IBus 绑定：

```bash
python3 -c "import gi; gi.require_version('IBus','1.0'); from gi.repository import IBus"
```

候选词乱码或没有中文：

检查 libpinyin 数据目录里有没有可读的 `*.bin` 文件。如果你的词库目录不在常见路径，
用 `LIBPINYIN_DATA_DIR` 重新运行安装脚本。

### 当前限制

这是一个最小可用输入法，不是完整 `ibus-libpinyin` 的替代品。目前没有图形设置界面、
模糊音配置、云拼音等功能。它的重点是：在没有 root 权限的机器上，用系统已有的
`libpinyin` 先把中文输入跑起来。

---

## English

A pure-Python IBus pinyin input engine for Linux desktops where you do not
have root access, but the system already ships `libpinyin` and its data files.
It talks directly to `libpinyin.so` through `ctypes` and registers itself as a
user-level IBus engine under `~/.local/share`.

### Requirements

- `libpinyin` and `libpinyin-data` must already be installed system-wide.
- Python must be able to import the IBus GObject Introspection bindings:

  ```bash
  python3 -c "import gi; gi.require_version('IBus','1.0'); from gi.repository import IBus"
  ```

- A GNOME or other IBus-integrated desktop session.

The installer checks common library and data locations automatically. For
custom layouts, set:

```bash
LIBPINYIN_PATH=/path/to/libpinyin.so \
LIBPINYIN_DATA_DIR=/path/to/libpinyin/data \
./install.sh
```

### Install

```bash
git clone https://github.com/DeTaiDong/rootless-pinyin.git
cd rootless-pinyin
./install.sh
```

Then log out and log back in once. This is required because `ibus-daemon` and
the session D-Bus broker cache component/service state at startup.

After logging back in, select **Pinyin (libpinyin, no-root)** from GNOME
Settings -> Keyboard -> Input Sources, or switch to it with `Super+Space`.

### Usage

Type pinyin such as `nihao`, then press `Space` or `Enter` to commit the best
candidate. Use number keys `1` to `9` to select candidates, `Backspace` to edit,
and `Esc` to cancel.

### What the Installer Does

- Copies engine files to `~/.local/share/ibus-pypinyin/`
- Registers an IBus component at `~/.local/share/ibus/component/pypinyin.xml`
- Writes `~/.config/environment.d/ibus-pypinyin.conf`
- Adds a user-level D-Bus service override for IBus with `--cache=refresh`
- Backs up an existing user-level IBus D-Bus service if one exists
- Adds `('ibus', 'pypinyin')` to GNOME input sources when possible

### Uninstall

```bash
./uninstall.sh
```

Then log out and log back in once.

### Limitations

This is a minimal engine, not a full replacement for `ibus-libpinyin`. It has no
GUI settings panel, fuzzy-pinyin UI, cloud pinyin, or advanced preference
management. It does support full-sentence segmentation through the real
libpinyin library and dictionary data.
