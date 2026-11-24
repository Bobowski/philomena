# Adaptive video

Moved from `AGENTS.md` (`## This app`) to keep that file under the 16,000-byte rule-loader cut.

Adaptive video: the camera measures motion from its preview (`app.motion`) and sends at 24 fps when `active`, 6 fps when `calm` (10 s), and 2 fps when `still` (60 s). `app.motion` ignores a brightness shift of the whole frame and pixel changes below 4 times the noise floor of the room, so grain in a dark room is not motion. A viewer that reports away (hidden, Screen off, or Sound only) gets no video track at all; the camera puts the track back when it looks again. `maxFramerate` and `applyConstraints` support differs per browser; the bitrate cap works everywhere. Audio always stays at full quality.
