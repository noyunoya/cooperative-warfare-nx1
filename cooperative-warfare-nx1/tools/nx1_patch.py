#!/usr/bin/env python3
"""NX1 co-op patcher (size-preserving).  Usage: python nx1_patch.py <zone.ffm> <out.ffm>
Edits plain-source GSC scripts stored inside an NX1 fastfile without changing ANY offset:
 - the script text keeps its exact length (edits are same-length),
 - the recompressed script is made EXACTLY its original compressed length (the engine asserts this),
 - the recompressed main zlib stream is made EXACTLY its original compressed length,
 so the chunk table and everything after the first stream stay byte-identical."""
import sys, zlib, struct, re, hashlib

VERSION = "nx1-coop 0.2.8"

def fit(old, new):
    """Replace `old` by `new` keeping the exact length (pads with spaces)."""
    new = new.encode() if isinstance(new, str) else new
    assert len(new) <= len(old), "replacement too long by %d bytes" % (len(new) - len(old))
    return new + b" " * (len(old) - len(new))

def edit_loadout(t):
    """common.ffm / maps/_loadout.gsc"""
    out = t
    # 1. Spec Ops loadout: drop the "give + take a Beretta" step (most zones do not contain that
    #    weapon, so the level crashed), and in its place define the loadout variables that
    #    nx_hospital's script expects (they were only set in the single-player loadout path).
    pat = re.compile(rb'\t// Ensures the Beretta[^\r\n]*\r\n\tforeach \( player in level\._players \)\r\n\t\{\r\n'
                     rb'\t\tplayer giveWeapon\( "beretta" \);\r\n\t\tplayer takeWeapon\( "beretta" \);\r\n\t\}')
    m = pat.search(out)
    if m:
        code = ('\tif(level._script=="nx_hospital"){level._main_gun="m4_silencer_reflex";'
                'level._gunSidearm="usp_silencer";level._primary_grenade="offensive_grenade";}')
        out = out[:m.start()] + fit(m.group(0), code) + out[m.end():]
    # 1b. default coop loadout: only player 2 gets the extra MP5/M1014 (player 1 already has the level's gun)
    pat = re.compile(rb'\tso_player_giveWeapon\( "mp5" \);\r\n\tso_player_giveWeapon\( "m1014" \);\r\n\tif \(num == 0\)\r\n'
                     rb'\t\tso_player_set_switchToWeapon\( "mp5" \);\r\n\telse\r\n\t\tso_player_set_switchToWeapon\( "m1014" \);')
    m = pat.search(out)
    if m:
        code = 'p2_g(num);'
        out = out[:m.start()] + fit(m.group(0), code) + out[m.end():]
    # 2. Co-op player body: use models that exist (Ghost in harbor/hospital, USMC James/Zach in border)
    for fname, line in ((b"so_body_player_ranger()", 'so_body_player_ranger(){m=p2_m(self==level._player2);self setModel(m[0]);self attach(m[1],"",true);}'),
                        (b"so_body_player_ranger_precache()", 'so_body_player_ranger_precache(){for(i=0;i<2;i++){m=p2_m(i);precachemodel(m[0]);precachemodel(m[1]);}}')):
        i = out.find(fname)
        if i < 0 or b"coop_body_us_army" not in out[i:i + 130]:
            continue
        e = out.find(b"\r\n", i)
        out = out[:i] + fit(out[i:e], line) + out[e:]
        done = True
    if b"p2_m(self" in out:
        f = ('p2_m(n){s=level._script;b="body_sp_";h="head_sp_";m=["body_hero_ghost_socom","head_hero_ghost_soccom"];'
             'if(s=="nx_border"){m=[b+"usmc_james",h+"usmc_james_james_body"];if(n==1)m=[b+"usmc_zach",h+"usmc_zach_zach_body"];}'
             'if(s=="nx_hospital"){m=[b+"spetsnaz_yuri",h+"spetsnaz_yuri_yuribody"];if(n==1)m=[b+"spetsnaz_vlad",h+"spetsnaz_vlad_vladbody"];}return m;}'
             'p2_g(n){g=::so_player_giveWeapon;if(level._script=="nx_border"){[[g]]("m4_grenadier_reflex");[[g]]("m1014_reflex");'
             'so_player_set_switchToWeapon("m4_grenadier_reflex");return;}if(n){[[g]]("mp5");[[g]]("m1014");so_player_set_switchToWeapon("m1014");}p2_s();}')
        f2 = 'p2_s(){if(isdefined(level._gunSidearm))so_player_giveWeapon(level._gunSidearm);}'
        print("helper bytes", len(f), len(f2))
        out = put_in_banners(out, [f, f2], 60)
    return out

def edit_platform(t):
    """nx_harbor.ffm / maps/_nx_moving_platform.gsc : put player 2 on the train too"""
    old_call = (b'\tlevel._player SetOrigin( player_start.origin );\r\n'
                b'\tlevel._player SetPlayerAngles( player_start.angles );')
    if old_call not in t:
        return t
    out = t.replace(old_call, fit(old_call, "\tp2_start( player_start );"))
    i = out.find(b"init_player_start()")
    j = out.find(b"//****", i)
    # the 4 banner comment lines right after the function
    k = j
    for _ in range(4):
        k = out.find(b"\r\n", k) + 2
    k -= 2
    func = ('p2_start(s){level._player SetOrigin(s.origin);level._player SetPlayerAngles(s.angles);'
            'if(isdefined(level._player2)){level._player2 SetOrigin(s.origin+AnglesToRight(s.angles)*40);'
            'level._player2 SetPlayerAngles(s.angles);}level thread p2_keep(s);}')
    # safety net: a player knocked off the moving tram (physics props) is put back on it
    keep = ('p2_keep(s){for(;;){wait 0.25;if(!isdefined(s))return;a=[level._player,level._player2];'
            'foreach(p in a){if(!isdefined(p))continue;d=s.origin-p.origin;'
            'if(abs(d[2])>500||length((d[0],d[1],0))>3000)p SetOrigin(s.origin+(0,0,8));}}}')
    print("platform helper bytes", len(func), len(keep))
    span = out[j:k]
    assert b"\r\n" in span
    out = out[:j] + fit(span, func) + out[k:]
    out = put_in_banners(out, [keep])
    return out

def edit_hospital_util(t):
    """nx_hospital.ffm / maps/nx_hospital_util.gsc : actor_teleport also moves player 2 next to player 1"""
    pat = re.compile(rb"\t\tactor SetPlayerAngles\( org\.angles \);(\r?\n)\t\tactor SetOrigin\( org\.origin \);")
    m = pat.search(t)
    if not m:
        return t
    out = t[:m.start()] + fit(m.group(0), "\t\tp2_tp(actor,org);") + t[m.end():]
    f1 = ("p2_c(o){f=AnglesToForward(o.angles);r=AnglesToRight(o.angles);e=o.origin+(0,0,50);"
          "c=[o.origin-r*40,o.origin+r*40,o.origin-f*48,o.origin+f*48];"
          "for(i=0;i<4;i++){if(BulletTracePassed(e,c[i]+(0,0,50),false,undefined))return c[i];}return c[0];}")
    f2 = ("p2_tp(a,o){a SetPlayerAngles(o.angles);a SetOrigin(o.origin);if(isdefined(level._player2)&&a==level._player)"
          "{level._player2 SetPlayerAngles(o.angles);level._player2 SetOrigin(p2_c(o));}}")
    print("bytes", len(f1), len(f2))
    out = put_in_banners(out, [f1, f2])
    return out

def comment_runs(t, minlen=200):
    """top-level comment blocks (outside any { }) of at least minlen bytes: [(start, end)]"""
    runs = []; cur = None; depth = 0; pos = 0
    for ln in t.split(b"\n"):
        s = ln.rstrip(b"\r")
        is_c = s.strip().startswith(b"//")
        if depth == 0 and is_c:
            if cur is None: cur = [pos, pos]
            cur[1] = pos + len(s)
        elif cur:
            runs.append(tuple(cur)); cur = None
        if not is_c:
            depth += s.count(b"{") - s.count(b"}")
        pos += len(ln) + 1
    if cur: runs.append(tuple(cur))
    return [(a, b) for a, b in runs if b - a >= minlen and a > 0]

def put_in_banners(out, funcs, minlen=200):
    """write each function text into a separate top-level comment block (same length)"""
    runs = comment_runs(out, minlen)
    assert len(runs) >= len(funcs), "not enough comment space"
    if minlen == 200:
        for (a, b), f in sorted(zip(runs, funcs), reverse=True):
            out = out[:a] + fit(out[a:b], f) + out[b:]
        return out
    # greedy: biggest function into the biggest block that still fits
    runs = sorted(runs, key=lambda r: r[1] - r[0], reverse=True)
    for f in sorted(funcs, key=len, reverse=True):
        for i, (a, b) in enumerate(runs):
            if len(f) <= b - a:
                out = out[:a] + fit(out[a:b], f) + out[b:]
                runs.pop(i)
                break
        else:
            raise AssertionError("no banner fits %d bytes" % len(f))
    return out

def edit_border(t):
    """nx_border.ffm / maps/nx_border_border.gsc : player 2 rides in the intro Humvee too"""
    o1 = b'\tplayer_rig linkTo( self, "tag_passenger" );\r\n\t//player_rig hide();'
    o2 = b'\t//self thread anim_single_solo( player_legs, "intro_ride" );'
    o3 = b'\t//player_legs delete();'
    if o1 not in t or o2 not in t or o3 not in t:
        return t
    out = t.replace(o1, fit(o1, '\tplayer_rig linkTo(self,"tag_passenger");\r\n\tself p2_in(player_rig);'))
    out = out.replace(o2, fit(o2, "\tself p2_go();"))
    out = out.replace(o3, fit(o3, "\tself p2_out();"))
    f_in = ('p2_in(r){if(!isdefined(level._player2))return;x=spawn_anim_model("player_rig");x.angles=r.angles;'
            'x.origin=r.origin+AnglesToRight(self.angles)*32;x linkTo(self,"tag_passenger");'
            'p=level._player2;p DisableWeapons();p playerLinkToDelta(x,"tag_player",1,80,80,60,20);level.p2r=x;}')
    f_go = ('p2_go(){if(isdefined(level.p2r))self thread anim_single_solo(level.p2r,"intro_ride");}'
            'p2_out(){if(isdefined(level.p2r)){p=level._player2;p unlink();level.p2r delete();p EnableWeapons();}}')
    return put_in_banners(out, [f_in, f_go])

def edit_border_util(t):
    """nx_border.ffm / maps/nx_border_util.gsc : player_start also places player 2"""
    pat = re.compile(rb"\tlevel\._player setOrigin\( player_start_struct\.origin \);(\r?\n)"
                     rb"\tlevel\._player setPlayerAngles\( player_start_struct\.angles \);")
    m = pat.search(t)
    if not m:
        return t
    out = t[:m.start()] + fit(m.group(0), "\tp2_ps(player_start_struct);") + t[m.end():]
    f = ("p2_ps(s){level._player setOrigin(s.origin);level._player setPlayerAngles(s.angles);"
         "if(isdefined(level._player2)){level._player2 setOrigin(s.origin+AnglesToRight(s.angles)*40);"
         "level._player2 setPlayerAngles(s.angles);}}")
    return put_in_banners(out, [f])

def edit_harbor_util(t):
    """nx_harbor.ffm / maps/nx_harbor_util.gsc : log every vehicle spawn (to find the null-model car) and skip empty-model spawners"""
    o1 = b"\t\tif( GetNumVehicles() < COUNT_CAP )"
    o2 = b"\tif( !IsDefined( level.vehicles ) )\r\n\t\tlevel.vehicle = [];"
    if o1 not in t or o2 not in t:
        return t
    out = t.replace(o1, fit(o1, "\t\tif(p2_vd(vehicle_spawner))"))
    out = out.replace(o2, fit(o2, '\tlevel.vehicle=[];p2_vd(GetEnt(targetname,"targetname"));'))
    f = ('p2_vd(s){a="?";b="?";c="?";if(isdefined(s.targetname))a=s.targetname;if(isdefined(s.vehicletype))b=s.vehicletype;'
         'if(isdefined(s.model))c=s.model;println("P2DBG veh "+a+" "+b+" "+c);if(c=="")return false;return GetNumVehicles()<50;}')
    return put_in_banners(out, [f])

EDITS = [
    ("maps/_loadout.gsc", edit_loadout),
    ("maps/nx_harbor_util.gsc", edit_harbor_util),
    ("maps/nx_border_border.gsc", edit_border),
    ("maps/nx_border_util.gsc", edit_border_util),
    ("maps/nx_hospital_util.gsc", edit_hospital_util),
    ("maps/_nx_moving_platform.gsc", edit_platform),
]

def find_stream0(f):
    count = struct.unpack(">I", f[0x1a:0x1e])[0]
    start = max(0x20, 0x20 + count * 12 - 16)
    for p in range(start, min(len(f) - 8, start + 0x400)):
        if f[p] == 0x78 and f[p + 1] in (0x01, 0x5e, 0x9c, 0xda):
            try:
                z = zlib.decompressobj(); z.decompress(f[p:p + 65536])
                return p
            except Exception:
                pass
    raise SystemExit("Could not find the main data stream.")

def best_compress(data, limit):
    best = None
    for level in (9, 8):
        for mem in (9, 8):
            for strat in (zlib.Z_DEFAULT_STRATEGY, zlib.Z_FILTERED):
                c = zlib.compressobj(level, zlib.DEFLATED, 15, mem, strat)
                out = c.compress(data) + c.flush()
                if best is None or len(out) < len(best):
                    best = out
    return best

def _build(data, level, splits):
    lv, mem, strat = level
    c = zlib.compressobj(lv, zlib.DEFLATED, 15, mem, strat)
    out = []; pos = 0
    for sp in splits:
        out.append(c.compress(data[pos:sp])); out.append(c.flush(zlib.Z_SYNC_FLUSH)); pos = sp
    out.append(c.compress(data[pos:])); out.append(c.flush())
    return b"".join(out)

def _hill(data, level, target, splits, rnd, lo, tries):
    """Add/remove flush points (each costs a few bytes, changes nothing in the output) until
    the stream is exactly `target` bytes."""
    splits = sorted(splits)
    cur = len(_build(data, level, splits))
    for _ in range(tries):
        if cur == target:
            return _build(data, level, splits)
        if cur < target:
            cand = sorted(splits + [rnd.randrange(lo + 1, len(data))])
        else:
            if not splits: return None
            cand = list(splits); cand.pop(rnd.randrange(len(cand)))
        n = len(_build(data, level, cand))
        if abs(n - target) <= abs(cur - target) or rnd.random() < 0.15:
            splits, cur = cand, n
    return None

def exact_compress(data, target):
    """zlib stream of `data` that is exactly `target` bytes long and inflates to `data`."""
    import random
    rnd = random.Random(12345)
    data = bytes(data)
    D, F = zlib.Z_DEFAULT_STRATEGY, zlib.Z_FILTERED
    for level in ((9, 9, D), (9, 8, D), (9, 9, F), (9, 8, F), (8, 9, D), (6, 9, D), (1, 9, D)):
        base = len(_build(data, level, []))
        if base > target:
            continue
        if len(data) <= 4_000_000:
            r = _hill(data, level, target, [], rnd, 0, 6000)
            if r: return r
            continue
        # big stream: uniform chunking to get close, then fine-tune only the tail
        tail_len = 300_000
        head_end = len(data) - tail_len
        lv, mem, strat = level
        def head_state(chunk):
            c = zlib.compressobj(lv, zlib.DEFLATED, 15, mem, strat)
            parts = []; pos = 0
            for sp in range(chunk, head_end, chunk):
                parts.append(c.compress(data[pos:sp])); parts.append(c.flush(zlib.Z_SYNC_FLUSH)); pos = sp
            parts.append(c.compress(data[pos:head_end]))
            return c, parts
        def tail_build(c0, splits):
            cc = c0.copy(); parts = []; p = head_end
            for sp in splits:
                parts.append(cc.compress(data[p:sp])); parts.append(cc.flush(zlib.Z_SYNC_FLUSH)); p = sp
            parts.append(cc.compress(data[p:])); parts.append(cc.flush())
            return parts
        def total(chunk):
            c0, hp = head_state(chunk)
            return sum(map(len, hp)) + sum(map(len, tail_build(c0, [])))
        lo_c, hi_c = 400, 20_000_000
        while hi_c - lo_c > max(50, lo_c // 50):
            mid = (lo_c + hi_c) // 2
            if total(mid) <= target - 3000: hi_c = mid
            else: lo_c = mid
        chunk = hi_c
        c0, hp = head_state(chunk)
        head_len = sum(map(len, hp))
        splits = []
        cur = head_len + sum(map(len, tail_build(c0, splits)))
        if cur > target:
            continue
        for _ in range(4000):
            if cur == target:
                return b"".join(hp) + b"".join(tail_build(c0, splits))
            if cur < target:
                add = max(1, (target - cur) // 60)
                cand = sorted(splits + [rnd.randrange(head_end + 1, len(data)) for _ in range(add)])
            else:
                if not splits: break
                cand = list(splits)
                for _ in range(max(1, (cur - target) // 60)):
                    if cand: cand.pop(rnd.randrange(len(cand)))
            n = head_len + sum(map(len, tail_build(c0, cand)))
            if abs(n - target) <= abs(cur - target) or rnd.random() < 0.1:
                splits, cur = cand, n
    return None

def main():
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(1)
    src, dst = sys.argv[1], sys.argv[2]
    print(VERSION, "- reading", src)
    f = open(src, "rb").read()
    if f[:4] != b"NXff":
        raise SystemExit("Not an NX1 fastfile.")
    p = find_stream0(f)
    z = zlib.decompressobj(); raw = bytearray(z.decompress(f[p:]))
    end = len(f) - len(z.unused_data)
    clen0 = end - p
    print("main stream: %d compressed -> %d raw bytes" % (clen0, len(raw)))
    done = 0
    for name, fn in EDITS:
        key = name.encode() + b"\x00\x78"
        i = raw.find(key)
        if i < 0 or raw[i - 16:i - 12] != b"\xff\xff\xff\xff":
            print("  %s: not in this zone, skipped" % name); continue
        clen, ln = struct.unpack(">II", raw[i - 12:i - 4])
        s = i + len(name) + 1
        zz = zlib.decompressobj(); text = zz.decompress(bytes(raw[s:s + clen]))
        assert len(text) == ln
        text2 = fn(text)
        if text2 == text:
            print("  %s: already patched / nothing to change, skipped" % name); continue
        assert len(text2) == ln, "edit changed the script length"
        text_final = text2
        exact = exact_compress(text_final, clen)
        if exact is None:
            # Make room by blanking the TEXT of // comments (same length, no effect on the game).
            tb = bytearray(text2)
            spans = []
            for m in re.finditer(rb"//[^\r\n]*", bytes(tb)):
                line_start = tb.rfind(b"\n", 0, m.start()) + 1
                if tb[line_start:m.start()].count(b'"') % 2 == 0 and m.end() - m.start() > 8:
                    spans.append((m.start() + 2, m.end()))
            blanked = 0
            while exact is None and spans:
                for a2, b2 in spans[:25]:
                    tb[a2:b2] = b" " * (b2 - a2); blanked += 1
                spans = spans[25:]
                assert len(tb) == ln
                text_final = bytes(tb)
                exact = exact_compress(text_final, clen)
            if exact is not None:
                print("  %s: blanked %d comment lines to make it fit (no effect on the game)" % (name, blanked))
        if exact is None or len(exact) != clen:
            raise SystemExit("  %s: could not size the script exactly" % name)
        assert zlib.decompressobj().decompress(exact) == text_final
        raw[s:s + clen] = exact
        print("  %s: patched (script re-sized to exactly %d bytes)" % (name, clen))
        done += 1
    if done == 0:
        print("Nothing to patch in this file."); return 1
    print("re-compressing the main stream to its exact original size (about a minute)...")
    c = exact_compress(bytes(raw), clen0)
    if c is None or len(c) != clen0:
        raise SystemExit("could not size the main stream exactly")
    out = f[:p] + c + f[end:]
    assert len(out) == len(f)
    # verify
    zv = zlib.decompressobj(); v = zv.decompress(out[p:])
    assert v == bytes(raw) and len(out[p:]) - len(zv.unused_data) == clen0, "verify failed"
    assert out[end:] == f[end:] and out[:p] == f[:p]
    open(dst, "wb").write(out)
    print("wrote %s (%d bytes, same size as the original; streams end exactly where they did). Verify OK." % (dst, len(out)))
    return 0

if __name__ == "__main__":
    sys.exit(main())
