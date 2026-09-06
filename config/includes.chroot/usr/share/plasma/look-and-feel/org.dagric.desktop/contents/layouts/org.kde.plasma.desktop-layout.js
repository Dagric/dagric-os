// SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
// SPDX-License-Identifier: GPL-3.0-or-later
// Initial layout only; never remove existing panels or alter an owner's layout.
if (panels().length === 0) {
    var preferences = new ConfigFile("dagric/installed-desktoprc", "Desktop");
    var familiar = preferences.readEntry("Layout") === "classic";
    var panel = new Panel;
    panel.location = "bottom";
    panel.height = 48;
    panel.floating = true;
    panel.lengthMode = "fill";
    panel.opacity = "adaptive";
    var menu = panel.addWidget("org.kde.plasma.kickoff");
    menu.currentConfigGroup = ["General"];
    menu.writeConfig("icon", "dagric-logo");
    // Initial favorites come from /etc/xdg/kicker-extra-favoritesrc, which
    // Kickoff reads before importing its model. Writing here is too late.
    if (!familiar) panel.addWidget("org.kde.plasma.panelspacer");
    var tasks = panel.addWidget(familiar ? "org.kde.plasma.taskmanager" : "org.kde.plasma.icontasks");
    tasks.currentConfigGroup = ["General"];
    tasks.writeConfig("launchers", ["applications:org.kde.dolphin.desktop", "preferred://browser",
        "applications:dagric-hub.desktop", "applications:dagric-desktop-settings.desktop"]);
    panel.addWidget("org.kde.plasma.panelspacer");
    panel.addWidget("org.kde.plasma.systemtray");
    panel.addWidget("org.kde.plasma.digitalclock");
    var wallpaper = preferences.readEntry("Wallpaper");
    if (["DagricObsidianPulse", "DagricArcticClean", "DagricAurora"].indexOf(wallpaper) >= 0) {
        var screens = desktops();
        for (var i = 0; i < screens.length; i++) {
            screens[i].wallpaperPlugin = "org.kde.image";
            screens[i].currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
            screens[i].writeConfig("Image", "file:///usr/share/wallpapers/" + wallpaper + "/contents/images/3840x2160.png");
        }
    }
}
