# Dagric OS — the default Konsole profile.
#
# A .colorscheme on its own changes nothing: Konsole only paints with a scheme
# a PROFILE asks for. This is the profile, and /etc/xdg/konsolerc is what makes
# it the default. Konsole finds this file by scanning $XDG_DATA_DIRS/konsole
# for *.profile, so /usr/share/konsole is enough — nothing has to register it.
#
# Name= IS NOT OPTIONAL. ProfileManager::loadProfile ends with
#   else if (newProfile->name().isEmpty()) {
#       qCWarning(...) << path << " does not have a valid name, ignoring."
# — a profile without it is dropped with only a debug-category warning, and the
# terminal silently stays Breeze. That failure is invisible without
# QT_LOGGING_RULES, which is exactly why it is written down here.
#
# Parent= IS DELIBERATELY ABSENT, and this is the mistake most Konsole profiles
# on the internet make. loadProfile already constructs the profile as
#   Profile::Ptr newProfile = Profile::Ptr(new Profile(builtinProfile()));
# so every key NOT set here inherits the built-in profile. Copying the usual
# `Parent=FALLBACK/` in adds nothing and risks an "invalid parent" path.
#
# No Font= for the same reason: the built-in parent supplies
# QFontDatabase::systemFont(FixedFont), which is whatever fontconfig actually
# resolved on this image. Naming a family here would be a guess — this build
# has no dedicated monospace package (only fonts-noto-core and
# fonts-liberation) and auto/config passes --apt-recommends false, so a font
# that exists on the developer's machine is not a font that exists on the ISO.
#
# HistoryMode is likewise not set. Its values are a C++ enum, not documented
# integers, and writing the wrong one gives NoHistory — a terminal that cannot
# scroll back at all. HistorySize is a plain int and the inherited default mode
# is already FixedSizeHistory, so raising the buffer alone is safe. 1000 lines
# is not enough to scroll back through a failed `apt` run, which is the single
# most likely reason a new owner opens this window twice.
#
# TerminalMargin: stock Konsole puts text 1px from the frame. 6 is breathing
# room, and matches the padding the rest of the Dagric surfaces use.

[Appearance]
ColorScheme=Dagric

[General]
Name=Dagric
TerminalMargin=6

[Scrolling]
HistorySize=10000
