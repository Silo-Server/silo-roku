# Sideload a build

Every Silo Roku tester build is on the
[Releases page](https://github.com/Silo-Server/silo-roku/releases) as a zip,
`silo-roku-<version>-<build>.zip`, that you can install on your own Roku
without the Roku Channel Store. You need a Roku running Roku OS 15.1 or later
and a phone or computer on the same network.

## 1. Turn on Developer Mode

1. With the Roku remote, press **Home** three times, **Up** twice, then
   **Right**, **Left**, **Right**, **Left**, **Right**.
2. Write down the address the screen shows, such as `http://192.168.1.50`.
3. Choose **Enable installer and restart**, accept the license, and set a
   password. The Roku restarts.

You only do this once. Roku's own guide is
[Developer setup](https://developer.roku.com/docs/developer-program/getting-started/developer-setup.md).

## 2. Download the build

This link always downloads the newest tester build:

<https://github.com/Silo-Server/silo-roku/releases/download/beta-latest/silo-roku-latest-beta.zip>

To pick a particular build, open it on the Releases page and download its
`silo-roku-<version>-<build>.zip` under **Assets**. Keep the file zipped.

## 3. Install it

1. On the phone or computer, open the address from step 1 in a browser.
2. Sign in with the user name `rokudev` and the password you set.
3. Choose **Upload**, pick the zip, and choose **Install** (some Roku OS
   versions say **Install with zip**).

Silo opens on the TV when the install finishes.

## Updating

Sideloaded apps don't update themselves. To update, download from the link in
step 2 again and install the zip the same way. It replaces the build you have.

## Good to know

- A Roku holds one sideloaded app. Sideloading another app replaces Silo.
- Turning Developer Mode off removes Silo.
- Signed `.pkg` files are not published and are not needed: Roku's installer
  takes the zip.
