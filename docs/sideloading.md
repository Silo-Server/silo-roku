# Sideload a build

Silo isn't in the Roku Channel Store yet, so you install it on your Roku
yourself from a web browser. Every tester build is on the
[Releases page](https://github.com/Silo-Server/silo-roku/releases) as a zip.
You need a Roku running Roku OS 15.1 or later (Settings → System → About) and a
phone or computer on the same network. The first time takes about ten minutes.

## 1. Turn on Developer Mode

1. On the Roku Home screen, press these buttons on the remote: **Home** three
   times, **Up** twice, then **Right**, **Left**, **Right**, **Left**,
   **Right**.
2. Write down the address the screen shows, such as `http://192.168.1.50`.
3. Choose **Enable installer and restart**, accept the license, and set a
   password. The Roku restarts.

You only do this once. Roku's own guide is
[Developer setup](https://developer.roku.com/docs/developer-program/getting-started/developer-setup.md).

## 2. Download the build

This link always downloads the newest tester build:

<https://github.com/Silo-Server/silo-roku/releases/download/beta-latest/silo-roku-latest-beta.zip>

Keep the file zipped: the Roku needs the `.zip` exactly as it downloads. Safari
on a Mac unzips downloads by default; if you get a folder instead of a zip,
turn off **Open "safe" files after downloading** in Safari's General settings
and download it again.

## 3. Open your Roku in a browser

On the phone or computer, go to the address from step 1. Sign in with the user
name `rokudev` and the password you set.

## 4. Upload and install

On the Development Application Installer page, choose **Upload**, pick the
zip, and choose **Install** (some Roku OS versions say **Install with zip**).
Silo opens on the TV when the install finishes.

## Updating

Sideloaded apps don't update themselves. To update, download from the link in
step 2 again and install the zip the same way. It replaces the build you have.
Silo's Settings screen shows which build you have, for example
`Silo 1.0.0 (12)`; the Releases page lists what changed in each build.

## Going back to an earlier build

If a build gives you trouble, open an earlier one on the
[Releases page](https://github.com/Silo-Server/silo-roku/releases), download
its `silo-roku-<version>-<build>.zip` under **Assets**, and install it the same
way. It replaces the Silo on your Roku.

## Checking the download

The Releases page lists a SHA-256 checksum next to each file. To compare it
with your download, run `shasum -a 256 <file>` on a Mac or Linux, or
`certutil -hashfile <file> SHA256` on Windows.

## Troubleshooting

- **The browser can't reach the Roku.** Use a device on the same network as
  the Roku, and type the address with `http://`, not `https://`. If you lost
  the address, find it under Settings → Network → About on the Roku.
- **The browser keeps asking for a password.** The user name is always
  `rokudev`. If you forgot the password, enter the button sequence from step 1
  again, disable the installer, then enable it with a new password. That
  removes Silo, so install the zip again afterwards.
- **The installer rejects the file.** Make sure you uploaded the `.zip`, not a
  folder or a file from inside it (see step 2), and that the Roku runs Roku OS
  15.1 or later.
- **Silo disappeared.** A Roku holds one sideloaded app, so sideloading
  another app replaces Silo, and turning Developer Mode off removes it.
  Install the zip again.
- **Something is wrong in Silo itself.**
  [Report it](https://github.com/Silo-Server/silo-roku/issues/new/choose) with
  the build number from Silo's Settings screen.

Signed `.pkg` files are not published and are not needed: Roku's installer
takes the zip.
