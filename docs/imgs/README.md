# README images

Assets referenced from the root [`README.md`](../../README.md).

| File | Use |
|------|-----|
| `logo.png` | Header / brand mark (same as app logo) |
| `app_icon.png` | Optional icon reference |
| `mainScreen.png` | Main window screenshot |

To refresh the logo from source assets:

```powershell
Copy-Item src\batch_stlink_flasher\assets\logo.png docs\imgs\logo.png -Force
```

Capture a new main-window screenshot manually (Help → About / live UI) and replace
`mainScreen.png`, or paste a PNG into this folder and update the README path.
