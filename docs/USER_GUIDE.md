# Black Flock Scheduler User Guide

## What The Site Is For

Black Flock Scheduler is used to manage the team's weekly availability, roster profiles, staff contacts, Overwatch patch notes, and Overwatch player statistics.

## Sign In

1. Open the site.
2. Enter the username and password provided by an administrator.
3. After sign-in, the weekly schedule page opens.

Self-registration is not available. If your password does not work, contact an administrator.

## Weekly Schedule

Players fill in their current-week availability in the `Schedule` tab.

Available entry types:

- `Time range` - a specific time block, for example `19:00-23:00`.
- `Available all day` - the player is available for the entire day.
- `Tentative` - the player is not sure yet.
- `Unavailable this day` - the player cannot play on that day.

To add availability:

1. Click `Add time` or the `+` button in your own schedule row.
2. Select a day.
3. Select the entry type.
4. For a time range, select start and end time.
5. Add a comment if needed.
6. Save the entry.

Comments are shortened inside schedule cards. Hover a card to see the full comment.

## Weekly Reset

The schedule stores only the current week. Every Monday, time entries are automatically cleared so players can fill in the new week.

Only schedule time entries are reset. Players, staff, BattleTags, Discord connections, roles, and statistics are not deleted.

## Profile

Open your profile from the top bar or the `Settings` sidebar item.

In the profile page you can:

- change your displayed player or staff name;
- edit BattleTag values;
- change your password;
- connect or disconnect Discord.

The account username is shown for reference and cannot be edited.

## Discord

Discord is connected only as a source for avatar and Discord handle. It is not a sign-in method.

After Discord is connected:

- avatar is loaded from Discord;
- Discord handle is loaded automatically;
- manual Discord handle editing is disabled.

If Discord is disconnected, the site falls back to the Black Flock logo avatar.

## Team Roster

The `Team` tab shows:

- players;
- player roles;
- BattleTags;
- Discord handles;
- staff members.

Users edit their own profile from the profile page. Administrators can manage team data in the Django admin.

## Overwatch Updates

The `Updates` tab shows official Blizzard patch notes.

Updates are synchronized automatically by cron. If the list is empty or outdated, an administrator can run synchronization manually from the admin panel or through the protected sync endpoint.

Patch note content is shown in the original English text.

## Overwatch Statistics

The `Stats` tab shows OverFast API data for each player's first BattleTag.

Available metrics:

- current competitive rank;
- calculated rating;
- winrate;
- match count;
- W/L;
- K/D;
- average eliminations;
- main hero by time played;
- team top heroes;
- rank distribution.

OverFast API limitations:

- real SR is not available;
- recent match history is not available;
- real win/loss streaks are not available;
- data depends on the Battle.net profile being available to OverFast.

If a player has no BattleTag or the profile is unavailable, the table shows a per-player status message.

## Admin Panel

Administrators can:

- change player order;
- change roles and role colors;
- link users to player or staff profiles;
- manually clear the schedule table;
- run Overwatch update synchronization;
- view Discord connection status.

Discord data in the admin is read-only. Manual Discord handle and avatar editing is not used.

## Common Issues

### I Cannot Add Time

Make sure your account is linked to a player profile. Staff profiles do not fill in the weekly schedule.

### Avatar Is Not Showing

Connect Discord in your profile. If the Discord account has no avatar, the site shows the Black Flock logo.

### Stats Did Not Load

Check your BattleTag in the profile page. The Battle.net profile must also be available to OverFast.

### Discord Says The Account Must Be Verified

That message comes from Discord. Verify the Discord account on Discord's side, then try connecting again.
