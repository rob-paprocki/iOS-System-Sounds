"""Shared logic for naming, categorising and identifying iOS sound files.

Used by the ingest and repo-build scripts. Kept dependency-free apart from
ffmpeg/fpcalc, which are invoked as subprocesses.
"""
import array
import hashlib
import json
import math
import os
import re
import subprocess
import sys

AUDIO_EXT = ('.caf', '.m4a', '.aiff', '.aif', '.wav', '.mp3', '.flac', '.aac',
             '.mp2', '.mp1', '.mpa', '.wave', '.ogg', '.oga', '.m4b', '.m4p',
             '.wma', '.opus', '.alac', '.aifc', '.mid', '.midi', '.amr', '.awb',
             '.dff', '.dsf', '.mka', '.ra', '.rm', '.snd', '.weba',
             '.tta', '.wv')
# .voc is deliberately absent. It is a Creative Labs audio format, but in iOS
# the only .voc files are Siri speech-recognition vocabularies under
# CDMFoundation.framework/VocFiles.bundle -- data, not sound.

# Container magic -> canonical extension, for files whose name lies.
MAGIC = {b'caff': '.caf', b'RIFF': '.wav', b'FORM': '.aiff',
         b'fLaC': '.flac', b'ID3': '.mp3', b'MThd': '.mid'}

GLOSS = {'ios': 'iOS', 'iphone': 'iPhone', 'ipad': 'iPad', 'macos': 'macOS',
         'watchos': 'watchOS', 'tvos': 'tvOS', 'ui': 'UI', 'ax': 'AX', 'fx': 'FX',
         'fm': 'FM', 'fmd': 'FMD', 'im': 'IM', 'sos': 'SOS', 'tty': 'TTY',
         'nfc': 'NFC', 'sim': 'SIM', 'id': 'ID', 'gps': 'GPS', 'rssi': 'RSSI',
         'gamecenter': 'Game Center', 'safetyalerts': 'Safety Alerts', 'aw': 'AW',
         'vo': 'VO', 'tts': 'TTS', 'db': 'dB', '3rdparty': '3rd Party',
         'sms': 'SMS', 'mms': 'MMS', 'vox': 'VOX', 'tv': 'TV', 'xpc': 'XPC',
         'phase': 'PHASE', 'hd': 'HD', 'lte': 'LTE', 'usb': 'USB', 'ap': 'AP',
         'vm': 'VM', 'sb': 'SB', 'os': 'OS', 'ct': 'CT', 'dtmf': 'DTMF',
         'sfx': 'SFX', 'vc': 'VC', 'gk': 'GK', 'fmr': 'FMR'}
KEEP = ('iOS', 'iPhone', 'iPad', 'macOS', 'watchOS', 'tvOS')


def humanize(stem):
    """Apple's internal asset name -> a readable title."""
    s = re.sub(r'__[A-Za-z0-9._-]+$', '', stem)
    loc = ''
    m = re.match(r'^([a-z]{2,3}-[A-Za-z]{2,4})[_-](.+)$', s)
    if m:
        loc, s = m.group(1), m.group(2)
        s = re.sub(r'^' + re.escape(loc) + r'[_-]', '', s)
        loc += ' '
    s = s.replace('_', ' ').replace('-', ' ')
    prot = {}
    for i, t in enumerate(KEEP):
        if t in s:
            prot['\x01%d\x01' % i] = t
            s = s.replace(t, '\x01%d\x01' % i)
    s = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', s)
    s = re.sub(r'(?<=[A-Z])(?=[A-Z][a-z])', ' ', s)
    s = re.sub(r'(?<=[a-z])(?=\d)', ' ', s)
    for k, v in prot.items():
        s = s.replace(k, v)
    s = re.sub(r'\s+', ' ', s).strip()
    out = []
    for w in s.split():
        if w in KEEP:
            out.append(w)
            continue
        g = GLOSS.get(w.lower())
        out.append(g if g else (w if not w[:1].islower() else w[:1].upper() + w[1:]))
    return (loc + ' '.join(out)).strip() or 'Untitled'


def tidy(stem):
    """Minimal cleanup, for stems that encode timings or IDs."""
    return re.sub(r'\s+', ' ', stem.replace('_', ' ')).strip()


def voice_title(stem):
    """Locale-prefixed TTS asset -> title, or None if it isn't one."""
    parts = stem.split('_')
    if not re.match(r'^[a-z]{2,3}-', parts[0]):
        return None
    loc, rest = parts[0], '_'.join(parts[1:])
    rest = re.sub(r'_?AX$', '', rest)
    if not rest:
        return loc
    m = re.match(r'^[a-z]{2,3}-[A-Za-z]{2,4}-?([A-Za-z])$', rest)
    if m:
        return '%s (%s)' % (loc, m.group(1))
    if re.match(r'^' + re.escape(loc) + r'\b', rest):
        rest = re.sub(r'^' + re.escape(loc) + r'[-_]?', '', rest)
    if re.match(r'^vp[_-]', rest) or re.match(r'^[a-z0-9]{1,3}\d', rest):
        return '%s %s' % (loc, rest)
    return ('%s %s' % (loc, humanize(rest))).strip()


# Framework / bundle basename -> destination category.
GROUPS = {
    'Find My': ['FMFindingUI', 'FindMyDevice', 'FindMy.app', 'NanoLeash',
                'FindMyDeviceHelperXPCService'],
    'Telephony & Messaging': ['TelephonyUtilities', 'FaceTimeNotificationUI',
                              'CallIntelligence', 'IMDaemonCore', 'ChatKit',
                              'ConversationKit', 'DropIn', 'SiriMessagesUICommon',
                              'MobilePhone.app', 'MobileSMS.app', 'Phone.app'],
    'Audio & Headphones': ['HeadphoneConfigs', 'HeadphoneSettingsUI',
                           'HeadphoneCommonUIKit', 'HearingUtilities', 'HearingTest',
                           'HearingModeService_Private', 'HearingModeSettingsUI',
                           'HearingModeUI', 'WorldAwareSpatialAudio', 'PHASE',
                           'MediaPlaybackCore', 'HeadGestures', 'AudioPasscode',
                           'AudioDiagnosticExtension.appex', 'Diagnostic-8290-EFD.appex'],
    'Camera & Photos': ['CameraEditKit', 'CameraUI', 'PhotosUICore', 'Tamale.app',
                        'OpusMagazineProducer.opplugin', 'OpusNewClassicProducer.opplugin',
                        'OpusOrigamiProducer.opplugin', 'MobileSlideShow.app'],
    'Home & Devices': ['Home', 'HomeDeviceSetup', 'DeviceSharing', 'TVRemoteUI',
                       'DeviceSharingServices', 'CompanionSetup.app', 'Tones.bundle',
                       'SeymourUI'],
    'Safety & Emergency': ['SafetyMonitor', 'SafetyMonitorApp.app'],
    'Accessibility/Other': ['CameraKit.axbundle', 'CameraUI.axbundle',
                            'MobileTimer.axbundle', 'VectorKit.axbundle',
                            'AccessibilitySettings.bundle', 'AssistiveTouch.app',
                            'sounds'],
    'Siri & Voices/Siri Interface': ['AssistantServices', 'SiriVOX', 'SiriSetup',
                                     'SiriReaderServices', 'SpeakerRecognition',
                                     'SpeechRecognitionCommandAndControl',
                                     'SystemVoiceAssistant.app', 'AdditionalResources',
                                     'Tones', 'ja-JP', 'Announce',
                                     'TextToSpeechVoiceBankingSupport'],
    'Ringtones & Alert Tones': ['Ringtones', 'Alerts'],
}
LOOKUP = {n: g for g, names in GROUPS.items() for n in names}


def category(ipsw_relpath, filename):
    """Map a path inside the extracted filesystem to a repo category folder."""
    d = os.path.dirname(ipsw_relpath)
    d = re.sub(r'^[^/]*__[^/]*/', '', d)          # strip the "BUILD__device" wrapper
    parts = d.split('/')
    base = parts[-1].replace('.framework', '') if parts else ''

    if 'SportsWorkout' in d:
        m = re.search(r'voices/(\w+)/(\w+)', d)
        if m:
            return 'Spoken Content/Nike+ Workout/%s/%s' % (m.group(2), m.group(1).title())
        return 'Spoken Content/Nike+ Workout'

    if 'FlexAudio' in d:
        m = re.search(r'FlexAudio/([^/]+)\.smsbundle(?:/([A-Z]+))?', d)
        code = re.match(r'([A-Za-z]+\d*)[_-]', filename)
        track = code.group(1) if code else 'Misc'
        stems = {'INTRO': 'Intro', 'BODY': 'Body', 'TRANS': 'Transition',
                 'CROSSFADE': 'Crossfade', 'OUTRO': 'Outro'}
        sub = stems.get(m.group(2)) if m and m.group(2) else None
        return 'Photos Memories/%s%s' % (track, '/' + sub if sub else '')
    if 'SoundScapesPickerAssets' in d:
        return 'Soundscapes'
    if 'VoiceServices_VoiceResources' in d:
        return 'Siri & Voices/Voice Assets'
    if 'Carrier Bundles' in d:
        return 'Telephony & Messaging/Carrier'
    if 'FindMyDevice' in d or 'FindMyDeviceHelper' in d:
        return 'Find My'
    if base == 'audio' and 'WebCore' in d:
        return 'System Frameworks/Web Core'
    if 'SiriTTSService.framework/AudioHintFiles/' in d:
        # One folder per locale. ja-JP was the only one until iOS 27.0.
        return 'Siri & Voices/Siri Interface'

    for suffix, cat in (
            ('UISounds/nano', 'UI Sounds/Watch'),
            ('UISounds/New', 'UI Sounds/New'),
            ('UISounds/Modern', 'UI Sounds/Modern'),
            ('UISounds', 'UI Sounds/iPhone'),
            ('VoicePreviews_AX', 'Siri & Voices/Voice Previews (Accessibility)'),
            ('InteractiveVoicePreviews', 'Siri & Voices/Voice Previews (Interactive)'),
            ('VoicePreviews', 'Siri & Voices/Voice Previews'),
            ('VoiceOverTouch.app/Sounds', 'Accessibility/VoiceOver'),
            ('AlertTones/EncoreInfinitum', 'Ringtones & Alert Tones/Encore Infinitum'),
            ('AlertTones', 'Ringtones & Alert Tones/Alert Tones'),
            ('Generic/Haptics/AudioResources', 'Haptics/Generic')):
        if d.endswith(suffix):
            return cat
    # The tuning folder is per device: V54 on iPhone 17 Pro Max, AID8028 on 18 Pro Max
    if re.search(r'Tunings/[^/]+/Haptics$', d):
        return 'Haptics/System'

    if base == 'MagnifierSupport':
        return 'Accessibility/Magnifier'
    if base == 'PersonalAudio':
        return 'Accessibility/Personal Audio'
    if base.endswith('.axuiservice'):
        return 'Accessibility/Live Speech'
    if 'UserNotifications/Bundles' in d:
        if 'safety' in base:
            return 'Safety & Emergency'
        return 'System Frameworks/' + humanize(
            base.replace('com.apple.', '').replace('.bundle', '').replace('.', ' '))
    if base in LOOKUP:
        return LOOKUP[base]
    if base.endswith('.app'):
        return 'System Frameworks/' + humanize(base[:-4])
    return 'System Frameworks/' + humanize(base)


def title_for(cat, stem):
    """Pick the right naming strategy for a category."""
    if cat.startswith('Photos Memories'):
        return tidy(stem)
    if cat.startswith('Siri & Voices/Voice'):
        return voice_title(stem) or humanize(stem)
    return humanize(stem)


def real_extension(path, fallback):
    """Trust the container magic over the filename."""
    with open(path, 'rb') as fh:
        head = fh.read(12)
    if head[4:8] == b'ftyp':
        return '.m4a'
    for magic, ext in MAGIC.items():
        if head.startswith(magic):
            return ext
    return fallback.lower()


def file_md5(path):
    m = hashlib.md5()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            m.update(chunk)
    return m.hexdigest()


def pcm_md5(path):
    """Hash the decoded audio, so re-wraps and lossless re-encodes collapse.

    Returns None when the file has no decodable audio stream.
    """
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-map', '0:a:0',
                        '-f', 's32le', '-acodec', 'pcm_s32le', '-'],
                       capture_output=True)
    if r.returncode != 0 or not r.stdout:
        return None
    return hashlib.md5(r.stdout).hexdigest()


def fingerprint(path):
    """Chromaprint fingerprint, for matching lossily re-encoded audio.

    Returns (duration, [int, ...]) or None. Very short sounds often yield
    nothing usable, which is expected and not an error.
    """
    r = subprocess.run(['fpcalc', '-raw', '-json', path], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    try:
        j = json.loads(r.stdout)
        fp = j.get('fingerprint')
        if not fp:
            return None
        return (j.get('duration'), fp)
    except ValueError:
        return None


def norm_pcm(path, rate=22050, max_seconds=12):
    """Decode to canonical mono 16-bit at a fixed rate, for comparing short sounds.

    Chromaprint needs several seconds of audio and returns nothing for typical
    system sounds, which have a median duration under half a second. This is
    the fallback that actually works at that length.
    """
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-map', '0:a:0',
                        '-ac', '1', '-ar', str(rate), '-t', str(max_seconds),
                        '-f', 's16le', '-acodec', 'pcm_s16le', '-'],
                       capture_output=True)
    if r.returncode != 0 or not r.stdout:
        return None
    raw = r.stdout[:len(r.stdout) // 2 * 2]
    return array.array('h', raw)


def pcm_similarity(a, b, length_tolerance=0.10):
    """Pearson correlation between two decoded signals. 1.0 is identical.

    Returns 0.0 when the durations differ by more than length_tolerance,
    which cheaply rejects unrelated sounds before doing the arithmetic.
    """
    if not a or not b:
        return 0.0
    la, lb = len(a), len(b)
    if max(la, lb) == 0 or abs(la - lb) / float(max(la, lb)) > length_tolerance:
        return 0.0
    n = min(la, lb)
    if n < 64:
        return 0.0
    sa = sum(a[:n]) / float(n)
    sb = sum(b[:n]) / float(n)
    num = va = vb = 0.0
    for i in range(n):
        da = a[i] - sa
        db = b[i] - sb
        num += da * db
        va += da * da
        vb += db * db
    if va <= 0 or vb <= 0:
        return 1.0 if va == vb else 0.0
    return num / math.sqrt(va * vb)


def fp_similarity(a, b):
    """Fraction of matching bits between two raw fingerprints, best offset.

    Chromaprint fingerprints are lists of 32-bit ints. Compares over the
    shorter length, sliding a small offset window to tolerate padding
    differences. 1.0 is identical.
    """
    if not a or not b:
        return 0.0
    best = 0.0
    span = min(len(a), len(b))
    if span == 0:
        return 0.0
    for offset in range(0, min(8, abs(len(a) - len(b)) + 1)):
        x = a[offset:offset + span] if len(a) >= len(b) else a[:span]
        y = b[:span] if len(a) >= len(b) else b[offset:offset + span]
        n = min(len(x), len(y))
        if n == 0:
            continue
        bits = sum(bin(x[i] ^ y[i]).count('1') for i in range(n))
        best = max(best, 1.0 - bits / (32.0 * n))
    return best


IMA_STEPS = [
    7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45,
    50, 55, 60, 66, 73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230,
    253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963,
    1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327,
    3660, 4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442,
    11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794,
    32767]
IMA_INDEX = [-1, -1, -1, -1, 2, 4, 6, 8]


def ima4_caf_to_wav(src, dst):
    """Decode an Apple IMA4 ADPCM CAF to 16-bit WAV. Returns False if it isn't one.

    ffmpeg cannot parse these, and afconvert only exists on macOS. Each packet
    holds 64 frames: per channel, a 2-byte header (predictor, step index)
    and 32 bytes of nibbles, low nibble first.
    """
    import struct
    import wave
    data = open(src, 'rb').read()
    if data[:4] != b'caff':
        return False
    pos, desc, audio = 8, None, None
    while pos + 12 <= len(data):
        kind, size = data[pos:pos + 4], struct.unpack('>q', data[pos + 4:pos + 12])[0]
        body = data[pos + 12:] if size < 0 else data[pos + 12:pos + 12 + size]
        if kind == b'desc':
            desc = struct.unpack('>d4sIIIII', body[:32])
        elif kind == b'data':
            audio = body[4:]                      # skip the edit count
        if size < 0:
            break
        pos += 12 + size
    if not desc or desc[1] != b'ima4' or audio is None:
        return False
    rate, channels = int(desc[0]), desc[5]
    per_packet = 34 * channels
    out = array.array('h')
    for p in range(0, len(audio) - per_packet + 1, per_packet):
        chans = []
        for c in range(channels):
            block = audio[p + 34 * c:p + 34 * (c + 1)]
            header = block[0] << 8 | block[1]
            pred = header & 0xFF80
            pred = pred - 0x10000 if pred & 0x8000 else pred
            index = min(header & 0x7F, 88)
            samples = []
            for byte in block[2:]:
                for nib in (byte & 0xF, byte >> 4):
                    step = IMA_STEPS[index]
                    diff = step >> 3
                    if nib & 1:
                        diff += step >> 2
                    if nib & 2:
                        diff += step >> 1
                    if nib & 4:
                        diff += step
                    pred = max(-32768, min(32767, pred - diff if nib & 8 else pred + diff))
                    index = max(0, min(88, index + IMA_INDEX[nib & 7]))
                    samples.append(pred)
            chans.append(samples)
        for frame in zip(*chans):
            out.extend(frame)
    if sys.byteorder == 'big':
        out.byteswap()
    with wave.open(dst, 'wb') as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(out.tobytes())
    return True


def walk_audio(root):
    """Yield every audio file under root, as paths relative to root.

    The relative path always uses '/', whatever the host, because category()
    parses it and ipsw_dir records it.
    """
    for dirpath, _, filenames in os.walk(root):
        for name in sorted(filenames):
            if name.lower().endswith(AUDIO_EXT):
                full = os.path.join(dirpath, name)
                yield full, os.path.relpath(full, root).replace(os.sep, '/')
