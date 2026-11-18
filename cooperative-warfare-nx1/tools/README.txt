NX1 co-op patch v0.2.8
======================
Run apply_coop_fix.bat or a per-level bat (needs Python 3). It patches common, nx_harbor, nx_hospital
and nx_border, keeps a .orig backup of each, and installs after you press Y.
The border file is big (~533 MB): expect several minutes and ~2 GB free RAM.
If you already patched earlier, it re-patches from the .orig backups.

Changes since 0.2.0 / 0.2.1:
- hospital: player 2 is placed next to player 1 (no longer under the map).
- border: player 2 now rides in the intro Humvee (rig placed 32 units to P1's
  side - seat position is a guess, tell me if it clips) and is placed next to P1
  at later level starts.
- Player bodies: border now uses the USMC squad models that are in its zone (P1 James, P2 Zach);
  harbor and hospital still use Ghost (re-patch common.ffm too, the body choice lives there).

0.2.4:
- hospital: both players now have Spetsnaz bodies (P1 Yuri, P2 Vlad) - Ghost does not exist in that zone.
- hospital: P2 spawn spot is checked with a line-of-sight trace and picks the first clear side
  (left, right, behind, ahead of P1) instead of always 40 units to the right (that was inside the wall).
- Re-run the whole bat: common (bodies), nx_hospital (spawn) both changed.

0.2.5:
- player 1 no longer gets the extra default MP5/M1014 (3 guns); only player 2 gets them.
- harbor: every vehicle spawn is now logged to console.log as "P2DBG veh <targetname> <vehicletype> <model>".
  If harbor crashes with "Script vehicle [(null)] needs [tag_wheel_front_left]", send console.log:
  the LAST P2DBG line before the crash is the culprit. Spawners with an empty model are skipped.

0.2.6:
- player 2 now also gets the level's sidearm (hospital: silenced USP; knife comes with it). Only common.ffm changed,
  so if you already patched 0.2.5 you only need to re-patch common (edit the bat's loop to "for %%N in (common)").

Per-level bats (like the MW3 kit): apply_common.bat, apply_harbor.bat, apply_hospital.bat, apply_border.bat
patch only that one zone. apply_coop_fix.bat still does all four. restore_originals.bat puts every .orig back.

0.2.7:
- harbor: if a player is knocked off the moving tram (random physics object) they are put back on it
  (checked every 0.25 s; triggers when more than 3000 units away horizontally or 500 vertically from the
  tram's player start; stops when the tram is deleted at the end). Only nx_harbor.ffm changed: run apply_harbor.bat.

0.2.8:
- border: both players now get the level's own guns (red-dot M4 + M203 and the red-dot M1014). The 0.2.5 change that
  stopped player 1 from getting the default extra guns had also removed them in Border.
  Only common.ffm changed: run apply_common.bat.
