// SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
// SPDX-License-Identifier: GPL-3.0-or-later
// Initial layout only; never remove existing panels or alter an owner's layout.
if (panels().length === 0) {
    var panel = new Panel;
    panel.location = "bottom";
    panel.height = 46;
    var menu = panel.addWidget("org.kde.plasma.kickoff");
    menu.currentConfigGroup = ["General"];
    menu.writeConfig("icon", "dagric-logo");
    menu.writeConfig("favorites", ["dagric-hub.desktop", "dagric-guide.desktop",
        "systemsettings.desktop", "org.kde.discover.desktop", "dagric-rewind.desktop",
        "preferred://browser", "org.kde.dolphin.desktop"]);
    panel.addWidget("org.kde.plasma.panelspacer");
    var tasks = panel.addWidget("org.kde.plasma.icontasks");
    tasks.currentConfigGroup = ["General"];
    tasks.writeConfig("launchers", ["applications:org.kde.dolphin.desktop", "preferred://browser",
        "applications:dagric-hub.desktop"]);
    panel.addWidget("org.kde.plasma.panelspacer");
    panel.addWidget("org.kde.plasma.systemtray");
    panel.addWidget("org.kde.plasma.digitalclock");
}
