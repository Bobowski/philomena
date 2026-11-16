## Design Context

### Users
Parents of a baby or a small child. They use Philomena mostly at night: in a dark nursery, in bed, half awake, often with one hand and a baby on the other arm. Two jobs:

- Set up the camera phone near the crib in under a minute, then walk away.
- Glance at the viewer phone and know at once: is it live, can I hear, is my baby fine.

The screen light of the camera phone can wake the baby. The screen light of the viewer phone hurts tired eyes at 3 a.m. In the day, the same parent checks the viewer in a bright room or outside in the sun.

### Brand personality
Calm, plain, trustworthy. A tool, not a gadget. Three words: clear, steady, sure.

The app speaks plain words to a parent ("Stays with the baby", "Reconnecting…"). It does not say "peer", "ICE", or "session".

### Two looks
Night first, with a day look for bright light. `static/js/theme.js` sets `data-theme` on `<html>` before the first paint.

- **Night**: black, with only red and amber light, the light that disturbs night vision least. The main action is tonal (a dark fill with a bright word), never a bright slab. The crying alert is deep red with light text. The picture strip and the camera's own preview are tinted red.
- **Day**: black on white, solid colours, heavier text. Readable in the sun. The main action is black with white text. The crying alert is solid red with white text.
- **Auto** (the default) follows the phone's light or dark setting, so the look changes when the phone does. The look switch (Auto, Night, Day) is on the home page, in the viewer's More → Picture tab, and in the camera's Settings.

Lights out (the camera) and Screen off (the viewer) are black with the night tokens in both looks.

### Style system
Tailwind v4 through the standalone binary. No daisyUI. `frontend/src/input.css` holds:

- The tokens, once per look: `--ground`, `--surface`, `--raised`, `--line`, `--ink`, `--muted`, `--hero`, `--accent`, `--live`, `--warn`, `--alarm`, the on-state and main-action colours, and the meter colours. Utilities read them: `bg-ground`, `bg-surface`, `border-line`, `text-ink`, `text-muted`, `text-accent`, `text-alarm`. Never write a hex colour in a view.
- The components: `btn` (`btn-primary`, `btn-ghost`, `btn-alarm`, `btn-sm`, `btn-lg`, `btn-block`, `btn-circle`, `btn-square`), `alert` (`alert-alarm`, `alert-warn`), `status` (`status-live`, `status-warn`, `status-alarm`), `input`, `join`, `seg` (tabs and the look switch), `list`, `badge`, `spinner`, `toast`, `dock`, `tile`, `sheet`, and `meter` (`meter-motion`, `meter-lg`, `meter-wide`).
- The glance view's layout, unlayered so it beats the picture view's utilities.

`app/common/ui.py` builds the shared parts: `top_bar`, `sheet`, `tile`, `look_switch`.

### The room pages
Each room page has the same frame: a top bar (Back, the room name, the status dot and one short status), then a stack of alerts, then what the thumb needs, then the controls. Back is the only way to the start page. On the camera, Back asks first, because it stops the camera.

**The viewer opens on the glance view.** One column:

- The word: Calm, Stirring, or Crying, as large as the screen allows, with one line under it ("Quiet since 20:04", "Moved at 20:31", "Since 20:04"). `static/js/glance.js` derives it from the camera's events: a cry holds "Crying" for 150 s, stirring, a loud sound, or movement hold "Stirring" for 60 s. Crying turns the word, the meters, and a glow at the top red.
- Two wide meters, Sound and Movement.
- "Turn on sound" while muted.
- The picture as a strip. A tap on it opens the picture view.
- Five large pads: Sound, Talk, Picture, Screen off, More.

**The picture view** is the video on the whole screen, with the meters in the top bar and a dock (Sound, Talk, Glance, Screen off, More) that hides while the picture plays. The viewer remembers which view a parent chose.

The camera has Invite, Viewers, Flip, Lights out, Settings in its dock, and the knock cards and the lights-out countdown above it.

A sheet never scrolls. More on the viewer has three tabs (Picture, Alerts, Room) of square tiles, and keeps one size on every tab. A toggle tile fills while it is on. Room holds the code, the connection, the camera battery, the last alert, and the other cameras. On the camera, Invite holds the QR, the code, Copy link, and Share. Viewers holds only the phones. Settings holds the name, a new code, the night history, and the look.

The code field takes 6 digits, "482 913", or a whole watch link. It keeps only the code.

Touch targets are 44 px or larger. Dock labels are nouns ("Sound"); the icon and the filled state show whether it is on. Every alert that can wait has a Dismiss with a word on it.

### Anti-references
A bright accent slab at night. A rainbow of status colours. An icon on every sentence. Gradient scrims as decoration. Pill chips floating on the video. A second palette in a view.

An icon belongs on a control, a status, or a short point. It names that thing.

### Design principles
1. Glanceable: state in one word and one colour, readable from arm's length.
2. Dark by care: the least light that does the job. At night, only red and amber. Lights out is black.
3. Readable in the sun: the day look is black on white, nothing pale.
4. Trust is shown: "Encrypted · direct" or "Encrypted · via relay", the number of people watching.
5. Set up once, then forget: the camera dims itself once someone watches.
6. Plain words for a parent, one instruction at a time.
