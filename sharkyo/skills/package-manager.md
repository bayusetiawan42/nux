# Package Management

Use this skill when the user wants to install, remove, update, or search for system packages.

## Execution Strategy

Detect the package manager from the OS. Use `apt` for Debian/Ubuntu, `dnf`/`yum` for Fedora/RHEL/CentOS, `pacman` for Arch. Commands run through a pty, so sudo password prompts can be answered in the user's terminal.

### Detect package manager

```bash
command -v apt && echo apt || command -v dnf && echo dnf || command -v pacman && echo pacman || command -v yum && echo yum
```

---

## apt (Debian/Ubuntu)

### Update package lists

```bash
sudo apt update
```

### Install a package

```bash
sudo apt install -y <PACKAGE>
```

### Remove a package

```bash
sudo apt remove -y <PACKAGE>
```

### Search for a package

```bash
apt search <QUERY>
```

### Show package info

```bash
apt show <PACKAGE>
```

### List installed packages

```bash
dpkg -l | grep <QUERY>
```

### Upgrade all packages

```bash
sudo apt update && sudo apt upgrade -y
```

### Clean up unused packages

```bash
sudo apt autoremove -y && sudo apt clean
```

---

## dnf (Fedora/RHEL)

### Install

```bash
sudo dnf install -y <PACKAGE>
```

### Remove

```bash
sudo dnf remove -y <PACKAGE>
```

### Search

```bash
dnf search <QUERY>
```

### Update all

```bash
sudo dnf upgrade -y
```

---

## pacman (Arch)

### Install

```bash
sudo pacman -S --noconfirm <PACKAGE>
```

### Remove

```bash
sudo pacman -Rs <PACKAGE>
```

### Search

```bash
pacman -Ss <QUERY>
```

### Update all

```bash
sudo pacman -Syu --noconfirm
```

---

## Parameters

- For all install/remove/upgrade commands: run them directly — sudo may prompt in the terminal, which is forwarded via the pty.
- For search/info commands: `review_output: true`.
- If the user doesn't specify package manager, detect it first with the detect command above (`review_output: true`), then install accordingly.

## Example

- **User**: "install ffmpeg"
- **Tool Call**:
  ```json
  {
    "name": "CMD",
    "arguments": {
      "command": "sudo apt install -y ffmpeg",
      "review_output_stderr": true
    }
  }
  ```
