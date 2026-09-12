# What changed, release by release

A researched account of when iOS gained or lost audio, assembled from Apple release
notes, Apple Newsroom, Wikipedia release histories and contemporary press coverage.
Every claim below was checked by a second, independent pass whose job was to refute it;
the ones that could not be refuted are what remain. Sources are listed per entry.

This is the documentary record, not a description of this repository's contents. Where
the two disagree, the extracted files win: see `sounds.json` for what is actually here.

## iOS 1.0

The original iPhone shipped with a self-composed set of 25 ringtones, with 'Marimba' as the default, plus the first UI sound set.

- Because the original iPhone was the only iPhone in existence in 2007, this whole set is the baseline every later diff is measured against.

  <https://en.wikipedia.org/wiki/IPhone_OS_1>
  <https://electronics.howstuffworks.com/composer-origin-iphone-marimba-ringtone.htm>
  <https://www.slashgear.com/1511674/historical-connection-behind-apple-iphone-famous-marimba-ringtone/>

## iOS 3.0

Voice Control, the Voice Memos app, and push notifications all arrived in the same release, each bringing its own audio surface.

- Voice Control (iPhone 3GS only) is a voice-command feature with its own cue tones; the exact filenames could not be confirmed from public sources and need direct IPSW inspection.
- Voice Memos ships recording start/stop UI sounds.
- Apple Push Notification Service is the first system-wide mechanism that lets any third-party app trigger a sound on an incoming push.

  <https://en.wikipedia.org/wiki/IOS_3>
  <https://en.wikipedia.org/wiki/Apple_Push_Notification_service>

## iOS 4.2.1

Apple added 17 new SMS and text alert tones, nearly tripling the original set of six, and allowed a distinct text tone per contact.

- At launch this was iPhone 4 only; iPhone 3GS did not receive the new tones with this release.
- The iPad release of this line is numbered 4.2; the iPhone build carrying the new tone files is 4.2.1, build 8C148.

  <https://www.apple.com/newsroom/2010/11/22Apples-iOS-4-2-Available-Today-for-iPad-iPhone-iPod-touch/>
  <https://www.engadget.com/2010-11-22-iphone-4-2-how-to-setting-custom-sms-alert-tones.html>
  <https://macenstein.com/2010/11/a-profanity-laden-tirade-against-the-new-ios-4-2-text-alert-sounds/>
  <https://www.macrumors.com/2010/11/22/ios-4-2-to-be-released-today-find-my-iphone-now-free/>

## iOS 4.3

Most of the text alert tones introduced in 4.2.1 were re-edited and shortened to well under a second after user complaints.

- A few tones, reported to include Minuet, Update and Anticipate, were left unchanged.
- This is an in-place edit of existing files: a 4.2.1-to-4.3 diff should show byte-different tones under the same filenames.
- A 'repeat alert up to 10 times' setting and a two-pulse vibration pattern for texts were added alongside.

  <https://www.idownloadblog.com/2011/03/14/messages-app-updated-in-ios-4-3/>
  <https://appleinsider.com/articles/11/06/08/inside_apples_ios_5_itunes_tone_store_will_offer_more_text_alert_options>

## iOS 5.0

Siri launched as an iPhone 4S exclusive, bringing the first on-device assistant activation and response audio cues.

- Siri was restricted to iPhone 4S at launch (9A334, 12 October 2011; 4S retail launch 14 October 2011) and refined for that device in 5.0.1 (9A405).
- The other tone-related change in this line was infrastructural - the iTunes Tone Store and more customisable alert categories - not a refresh of Apple's own default tone files.

  <https://ipsw.me/download/iPhone4,1/9A405/>
  <https://www.iphonefaq.org/archives/971716>
  <https://www.slashgear.com/iphone-4-siri-port-made-legally-possible-by-apple-with-ios-5-0-1-update-today-16202798/>
  <https://appleinsider.com/articles/11/06/08/inside_apples_ios_5_itunes_tone_store_will_offer_more_text_alert_options>

## iOS 6.0

Apple Maps replaced Google Maps and added spoken turn-by-turn driving directions, a navigation voice that did not exist in earlier releases.

- Spoken directions were limited to iPhone 4S and later and cellular iPad 2 and later at launch.
- Do Not Disturb also arrived; it suppresses sounds rather than adding any asset.

  <https://www.apple.com/newsroom/2012/06/11Apple-Previews-iOS-6-With-All-New-Maps-Siri-Features-Facebook-Integration-Shared-Photo-Streams-New-Passbook-App/>
  <https://en.wikipedia.org/wiki/IOS_6>

## iOS 7.0

The flat-design overhaul came with the largest sound change in the platform's history: 27 new ringtones, 12 new alert tones, the old set demoted to a 'Classic' menu, the unlock chime deleted, and a male Siri voice added.

- 'Opening' replaced 'Marimba' as the default ringtone. New alert tones include Aurora, Bamboo, Chord, Hello, Note, Popcorn, Pulse and Synth.
- Every pre-iOS 7 ringtone and alert tone was kept but moved into a 'Classic' sub-category of the tone picker, so those files should still be physically present.
- The slide-to-unlock chime, present unchanged since the original iPhone, was removed; the separate lock (screen-off) sound was kept. Only jailbreak tweaks could restore it. This is sourced from blog coverage of those tweaks rather than an Apple statement.
- Siri's US English voice was redesigned and a male voice option was offered for the first time, doubling the per-locale voice-preview assets in supported regions.

  <https://www.idownloadblog.com/2013/09/10/hands-on-with-ios-7-new-rigntones-and-alerts-sounds/>
  <https://9to5mac.com/2013/09/10/listen-to-ios-7s-new-ringtones-and-text-tones-video/>
  <https://www.idownloadblog.com/2014/01/18/unlocksound7/>
  <https://www.redmondpie.com/how-to-get-classic-slide-to-unlock-sound-back-on-ios-7-lock-screen/>
  <https://www.gottabemobile.com/how-to-get-old-iphone-ringtones-back/>
  <https://www.ibtimes.com/apple-reveals-siri-will-now-have-male-voice-option-ios-7-release-1307167>

## iOS 7.1

New, more natural Siri voices shipped for UK English, Australian English and Japanese only, replacing the 7.0-era voices in those locales.

- This is direct evidence that a voice-asset overhaul can land on a minor release and cover only a subset of locales.

  <https://appleinsider.com/articles/14/02/04/first-listen-new-natural-sounding-siri-voices-for-the-uk-australia-and-japan>
  <https://www.idownloadblog.com/2014/01/20/uk-siri-male-female-voices/>

## iOS 8.0

Siri's voices became selectable as the system speech voice for VoiceOver, Speak Screen and Speak Selection; the macOS 'Alex' voice came to iOS; and 'Hey Siri' hands-free activation launched.

- 'Hey Siri' at this point required the device to be plugged in.
- This is the point where VoiceOver's voice list starts overlapping with Siri's TTS assets, which matters for de-duplicating the corpus.
- Siri also gained roughly 22 additional languages per WWDC 2014.

  <https://dyslexiahelp.umich.edu/latest/apples-new-ios-8-has-several-big-accessibility-improvements>
  <https://www.idownloadblog.com/2016/02/17/how-to-select-siri-voices-for-voiceover/>
  <https://www.macstories.net/stories/a-timeline-of-ios-accessibility-it-started-with-36-seconds/>
  <https://en.wikipedia.org/wiki/Siri>

## iOS 9.0

The built-in Nike + iPod app was deleted, taking its spoken workout prompts with it, while 'Hey Siri' became always-on and the iPhone 6s added the Taptic Engine.

- Nike + iPod had been bundled since the iPhone 3G era with its own spoken workout-progress audio and selectable male/female voice packs. It was removed in iOS 9 with no user-facing deprecation notice. This is corroborated by Apple Support Community and forum threads rather than press or primary sources, so confidence is medium.
- 'Hey Siri' no longer required the device to be plugged in, and gained per-owner voice recognition.
- iPhone 6s and 6s Plus introduced the Taptic Engine with 3D Touch, a linear actuator producing haptic pulses earlier hardware could not.

  <https://discussions.apple.com/thread/7230303>
  <https://discussions.apple.com/thread/7220241>
  <http://www.dslreports.com/forum/r30305275-Nike-iPod-Built-in-removed-in-iOS9>
  <https://en.wikipedia.org/wiki/Siri>
  <https://en.wikipedia.org/wiki/IPhone_6S>

## iOS 10.0

Apple redesigned the lock and keyboard-click sounds, and rebuilt Siri's speech synthesis on a deep-learning model for the first time.

- Apple's own description of the release calls out 'new sound effects for locking the device and for keyboard clicks'.
- Apple's machine learning research writeup A/B-compares iOS 9, iOS 10 and iOS 11 Siri voices and places the move from concatenative unit selection to a deep mixture density network at iOS 10, not iOS 11.

  <https://en.wikipedia.org/wiki/IOS_10>
  <https://machinelearning.apple.com/research/siri-voices>

## iOS 10.3

Find My AirPods added a 'Play Sound' action that makes a lost AirPod chirp.

- The chirp is most likely stored in the AirPods' own firmware rather than in the iOS filesystem; this needs confirmation at extraction time rather than assumption.

  <https://www.macworld.com/article/229840/how-to-use-find-my-airpods-in-ios-10-3.html>
  <https://time.com/4646024/ios-10-3-beta-airpods/>

## iOS 11.0

Siri was re-recorded with new male and female US English voice talent, retiring the 2011-era voice database, and Emergency SOS added a loud siren-style countdown sound.

- Apple recorded roughly 20 hours of speech from new voice talent, generating one to two million audio segments, at a higher sample rate than the earlier system.
- The Emergency SOS Countdown Sound plays during the auto-call countdown, for example after pressing the side button five times, and is toggleable in Settings.
- Community reports claim the pre-2017 Siri voices survive inside VoiceOver's voice picker under different names (US Aaron/Nicky, UK Arthur/Martha, Australian Catherine/Gordon). This is forum-sourced only and unverified.

  <https://machinelearning.apple.com/research/siri-voices>
  <https://www.apple.com/newsroom/2017/06/ios-11-brings-new-features-to-iphone-and-ipad-this-fall/>
  <https://www.romper.com/p/how-to-turn-on-the-emergency-sos-countdown-sound-in-ios-11-because-mistakes-happen-2912206>
  <https://applevis.com/forum/ios-ipados/why-dont-we-have-all-old-siri-voices-after-release-ios-11>

## iOS 11.1

'Reflection' shipped as a new default ringtone, playable only on iPhone X even though the file sits in the shared 11.1 image (build 15B93).

- 'Opening' remained the default on all other models.
- AppleVis reports also describe an audible Face ID unlock chime on the earliest Face ID devices that 'disappeared rather quickly' from later builds. This is forum-sourced and low confidence.

  <https://9to5mac.com/2017/11/01/iphone-x-exclusive-default-ringtone-reflection/>
  <https://www.macrumors.com/2017/11/01/iphone-x-reflection-ringtone/>
  <https://www.applevis.com/bugs/ios/missing-audible-tone-after-your-device-has-been-successfully-unlocked-face-id>

## iOS 12.0

Live Listen, which streams the device microphone to Made-for-iPhone hearing aids, was extended to work with AirPods.

- This is a routing change to an existing hearing-accessibility feature, not a new bundled asset.

  <https://www.macstories.net/stories/a-timeline-of-ios-accessibility-it-started-with-36-seconds/>

## iOS 13.0

Siri's US English voice moved to fully generated Neural TTS, new Indian English voices shipped, and the Voice Control accessibility feature added command-confirmation sounds.

- Neural TTS generates speech from a learned model at runtime instead of splicing recorded clips, so the on-disk asset type itself changes versus iOS 12.
- New male and female Indian English Siri voices shipped along with a matching Indian English Maps navigation voice.
- Voice Control includes a setting to play a sound when a command is recognised.

  <https://www.engadget.com/2019-06-03-siri-now-sounds-more-like-a-human.html>
  <https://www.shacknews.com/article/112048/apple-announces-neural-tts-support-for-siri-at-wwdc-2019>
  <https://www.thequint.com/tech-and-auto/tech-news/soon-siri-will-be-speaking-to-you-in-desi-english-accent>
  <https://www.macrumors.com/guide/voice-control/>

## iOS 13.6

Apple News added Apple News Today and narrated Apple News+ audio, which Apple stated required iOS 13.6.

- These are streamed or cached from Apple's servers on demand and are very unlikely to be present as files in the IPSW; only a player chime, if one exists, would be.

  <https://www.apple.com/newsroom/2020/07/apple-news-launches-new-audio-features-expands-local-news-offerings-for-readers/>
  <https://www.macstories.net/news/apple-releases-ios-136-with-apple-news-audio-features-and-expanded-local-news-coverage-plus-digital-car-key-support/>

## iOS 14.0

Sound Recognition shipped, listening on-device for alarms, sirens, doorbells, knocking, running water, animals, appliance beeps, car horns and crying, and Spatial Audio arrived for AirPods Pro.

- Sound Recognition is a classifier rather than an obvious sample library, but the filesystem is worth checking for exemplar audio shipped alongside the model.
- Spatial Audio is a rendering-pipeline change, not a discrete sound file, and required a companion AirPods Pro firmware update.

  <https://www.macrumors.com/2020/06/23/ios-14-sound-recognition-alarms-doorbells/>
  <https://en.wikipedia.org/wiki/IOS_14>
  <https://www.macrumors.com/guide/ios-14-airpods/>

## iOS 14.5

Two new US English Siri voices were added, the gender picker was removed in favour of a 'Variety' picker, and Precision Finding added approach audio cues in Find My.

- Siri also stopped defaulting new setups to a female voice; users are prompted to choose.
- Precision Finding's approach cue is played by the iPhone and is a legitimate IPSW asset candidate. It is distinct from an AirTag's own separation beep, which comes from AirTag firmware and never appears in an iPhone image.

  <https://9to5mac.com/2021/03/31/ios-14-5-siri-no-longer-defaults-to-a-female-voice-two-new-voices-added/>
  <https://appleinsider.com/articles/21/03/31/siri-gets-two-new-voices-user-choice-at-setup-in-ios-145>
  <https://www.apple.com/newsroom/2021/04/apple-introduces-airtag/>
  <https://www.macrumors.com/how-to/use-precision-finding-airtag/>

## iOS 15.0

Background Sounds shipped with six looping ambient tracks, Announce Notifications added a pre-announcement tone, and FaceTime gained spatial audio and new microphone modes.

- The six tracks are Balanced Noise, Bright Noise, Dark Noise, Ocean, Rain and Stream. These are static looping files and are the clearest new extractable audio in this era.
- Announce Notifications plays a tone before speaking a notification through connected headphones; the spoken part is dynamic TTS.
- FaceTime spatial audio, Voice Isolation and Wide Spectrum are real-time processing, not new files.

  <https://support.apple.com/HT212775>
  <https://support.apple.com/en-us/109346>
  <https://9to5mac.com/2021/10/20/how-to-announce-notifications-on-iphone-siri-ios-15/>
  <https://support.apple.com/en-us/101993>

## iOS 15.4

A fifth American Siri voice, gender-neutral and internally called 'Quinn', was added.

- Labelled 'America (Voice 5)' in Settings; Apple described it as recorded by a member of the LGBTQ+ community.

  <https://www.macrumors.com/2022/02/22/ios-15-4-new-siri-voice/>
  <https://techcrunch.com/2022/02/24/siri-gains-a-new-gender-neutral-voice-option-in-latest-ios-update/>

## iOS 16.0

VoiceOver gained the Eloquence synthesizer and several new voices, the Find My ping sound was redesigned, and iPhone 14 added Crash Detection audio and an optional power-on/off chime.

- VoiceOver added Eloquence, higher-quality US English voices (Evan, Nathan, Zoe), novelty voices (Bells, Bubbles, Jester, Superstar), and speech support for 20+ more languages.
- Find My's device-ping sound changed from the classic radar-blip to a newer ringtone-style sound, observed in iOS 16 beta 5 (8 August 2022) and assumed to have reached 16.0 (20A362).
- Crash Detection and Power On & Off Sounds are iPhone 14 features and shipped on that device's out-of-box build 16.0.1 (20A371).

  <https://afb.org/aw/23/10/18078>
  <https://9to5mac.com/2022/08/08/find-my-new-sound-alert-ios-16/>
  <https://support.apple.com/en-us/104959>
  <https://www.macrumors.com/2022/09/07/iphone-14-mac-like-startup-sound/>

## iOS 17.0

More than 20 new ringtones and more than 10 new alert tones were added, the default alert tone changed from Tri-tone to Rebound, Live Voicemail added a chime, and Personal Voice and Live Speech introduced user-generated synthetic speech.

- New ringtones include Arpeggio, Breaking, Canopy, Chalet, Chirp, Daybreak, Departure, Dollop, Journey, Kettle, Mercury, Milky Way, Quad, Radial, Scavenger, Seedling, Shelter, Sprinkles, Steps, Storytime, Tease, Tilt, Unfold and Valley. 'Reflection' remained the default ringtone.
- Tri-tone was not removed, only displaced as the default.
- Live Voicemail plays a brief chime when a caller starts leaving a message.
- Personal Voice builds an on-device voice model from about 15 minutes of the user's recorded speech (A12 Bionic and later); Live Speech speaks typed text during calls and in person.
- The Siri wake phrase was shortened so 'Siri' works without 'Hey'.
- NameDrop is reported to have its own sound effect, but only in social-media demo video, not written press. Treat as unverified.

  <https://www.macrumors.com/how-to/try-new-ringtones-text-tones-iphone/>
  <https://en.wikipedia.org/wiki/IOS_17>
  <https://www.apple.com/newsroom/2023/06/ios-17-makes-iphone-more-personal-and-intuitive/>
  <https://www.apple.com/newsroom/2023/05/apple-previews-live-speech-personal-voice-and-more-new-accessibility-features/>
  <https://voicebot.ai/2023/06/05/apple-changing-hey-siri-wake-word-to-just-siri-and-other-wwdc-news/>

## iOS 17.1

The Siri voice assets used by VoiceOver were repackaged at much lower fidelity, reportedly shrinking the US English download from roughly 450 MB to roughly 66 MB.

- VoiceOver users described the result as grainy and stuttering; the larger files reportedly remained reachable only via the per-activity voice picker under Accessibility > VoiceOver > Activities.
- This is sourced entirely from AppleVis forum threads, reached through search-engine snippets because the site returns HTTP 403 to automated fetching. It should be confirmed by comparing actual asset sizes between a 17.0 and a 17.1 image rather than trusted as reported.

  <https://applevis.com/forum/ios-ipados/has-anyone-noticed-siri-voices-voiceover-sound-terrible-ios171>
  <https://applevis.com/forum/ios-ipados/using-siri-voices-aren-t-static-voiceover>

## iOS 17.2

A 'Default Alerts' control was added to Settings, letting users pick the system-wide default notification sound and reinstate Tri-tone.

- No new sound file; it exposes existing sounds and confirms none of the pre-17.0 tones were deleted.

  <https://9to5mac.com/2023/11/28/ios-17-2-beta-4-change-default-notification-sound/>
  <https://www.macworld.com/article/2156872/ios-17-2-change-default-alert-notification-sound-tri-tone-rebound.html>

## iOS 18.0

Two new Background Sounds ('Night' and 'Fire') were added, Vocal Shortcuts let users record custom trigger phrases, and Music Haptics synced the Taptic Engine to Apple Music playback.

- Night and Fire extend the six tracks introduced in 15.0 to eight.
- Vocal Shortcuts stores user-recorded speech rather than shipping Apple audio.
- Music Haptics produces haptics, not audio.
- iPhone 16 models added Audio Mix in Photos, post-capture remixing of video audio using the four-microphone array; it is hardware-gated to that generation.

  <https://www.macrumors.com/2024/07/10/ios-18-new-background-sounds/>
  <https://www.idownloadblog.com/2024/07/10/apple-ios-18-background-sounds-night-fire-ambient-soundscapes/>
  <https://www.afb.org/blog/entry/ios-18-accessibility-features>
  <https://www.macrumors.com/how-to/iphone-16-edit-spatial-audio-in-video-audio-mix/>

## iOS 18.1

AirPods Pro 2 gained an FDA-authorised Hearing Test, Hearing Aid and Hearing Protection, paired with this release rather than 18.0.

- The Hearing Test is on-device pure-tone audiometry, so calibrated test tones are played through the earbuds; whether those tones live in the iOS image or in AirPods firmware (7B19 and later) needs checking at extraction time.
- 18.1 is build 22B83, released 28 October 2024.

  <https://www.apple.com/newsroom/2024/09/apple-introduces-groundbreaking-health-features/>
  <https://www.forbes.com/sites/anthonykarcz/2024/10/31/how-to-take-a-hearing-test-in-ios-181-with-airpods-pro-2/>

## iOS 26.0

Seven new ringtones and eight new Background Sounds were added, and Live Translation and Workout Buddy introduced new generated-speech features.

- The new ringtones are six remixed variants of Reflection (Buoyant, Dreamer, Pond, Pop, Reflected, Surge) plus one wholly new tone, 'Little Bird'. These are the first new stock ringtones since iOS 17.
- The eight added Background Sounds are Babble, Steam, Airplane, Boat, Bus, Train, Rain on Roof and Quiet Night, doubling the set from eight to sixteen.
- Live Translation speaks translations aloud in Phone calls and through supported AirPods; Workout Buddy narrates workout stats using a text-to-speech model built from Apple Fitness+ trainer voice data. Both are runtime synthesis, so look for voice-model resources rather than new .caf files.
- A new Siri listening tone is reported alongside the Liquid Glass redesign, sourced from an accessibility roundup rather than Apple.
- The legacy system sounds (lock/unlock, charger connect, call hang-up, keyboard clicks) were explicitly not redesigned; VoiceOver users noted the mismatch with the new visual language.
- Widespread reports of 'no notification sound after updating' are a Focus/text-tone reset bug, not an asset removal.

  <https://www.macrumors.com/how-to/new-iphone-ringtones-ios-26/>
  <https://9to5mac.com/2025/09/30/ios-26-adds-seven-brand-new-iphone-ringtones-listen-here/>
  <https://www.macrumors.com/2025/06/09/ios-26-background-sounds/>
  <https://www.apple.com/newsroom/2025/09/new-apple-intelligence-features-are-available-today/>
  <https://afb.org/blog/entry/ios-26-accessibility-features>
  <https://discussions.apple.com/thread/256145526>

## iOS 26.1

New European Portuguese Siri voices were added, distinct from the existing Brazilian Portuguese set.

- Confirmed by Apple's own SDK release notes, which document known issues with voice previews falling back to legacy pt-BR and with word stress in 'the initial pt-PT Siri Voices'.
- This is the clearest case in the 26 line of a voice set changing on a minor release rather than at .0.

  <https://developer.apple.com/documentation/ios-ipados-release-notes/ios-ipados-26_1-release-notes>

## iOS 26.2

Reminders gained an 'Urgent' toggle that fires a full alarm through the new AlarmKit framework instead of a notification chime.

- This adds an audio-triggering surface rather than, most likely, new files; worth a spot-check against the 26.0 and 26.1 tone inventories to confirm.

  <https://www.applevis.com/blog/apple-releases-ios-262-ipados-262-new-airdrop-feature-reminders-alarms-airpods-live>
  <https://www.macrumors.com/2025/12/24/new-things-iphone-can-do-ios-26-2/>

## iOS 26.4

A framework was added that lets third-party audio accessories report headphone information for automatic audio switching, available to developers only.

- Apple's release notes state it is developer-testing-only on iPhone and iPad in 26.4, with customer availability limited to the EU in a later 26.x release. No new audio assets, and not a reason to download 26.4 on its own.

  <https://developer.apple.com/documentation/ios-ipados-release-notes/ios-ipados-26_4-release-notes>

## Builds that exist on one phone only

A phone's launch build is often exclusive to it, and is then the only image its
hardware-specific audio ever shipped in.

- Original iPhone (iPhone OS 1.0): the founding set of 25 ringtones including Marimba, plus the first UI sound set. Every later diff is measured against this. https://en.wikipedia.org/wiki/IPhone_OS_1
- iPhone 4S (iOS 5.0 / 5.0.1, 9A334 / 9A405): Siri's activation and response audio cues, 4S-exclusive for over a year. https://ipsw.me/download/iPhone4,1/9A405/
- iPhone 6s / 6s Plus (iOS 9.0): first Taptic Engine, producing 3D Touch peek/pop and Quick Action haptics that no earlier iPhone hardware can generate. Every later haptic feature builds on this actuator. https://en.wikipedia.org/wiki/IPhone_6S
- iPhone 7 / 7 Plus (iOS 10.0.1, build 14A403): reported to have shipped on its own build while other devices stayed on 10.0 (14A346). First iPhone with no headphone jack and a non-moving haptic home button. Exclusivity is attested by IPSW mirrors but was not positively confirmed.
- iPhone X (iOS 11.1, build 15B93): the 'Reflection' ringtone was playable only on iPhone X, although the file itself is in the shared 11.1 image - software gating, not build exclusivity. AppleVis users also report a Face ID unlock chime present on the earliest Face ID devices that disappeared from later builds; low confidence. https://www.macrumors.com/2017/11/01/iphone-x-reflection-ringtone/
- iPhone 11 (iOS 13 era): first iPhone with the U1 ultra-wideband chip. The audio payoff - Precision Finding's directional approach cues - did not ship until iOS 14.5, so the device-launch build and the audio-introducing build are different releases. https://www.macrumors.com/2021/04/20/airtag-u1-chip-precision-finding/
- iPhone SE (2nd generation, 2020): received iOS 13.4.1 build 17E8258, which no other device got (general devices got 17E262). Confirmed device-exclusive build tree; no audio change documented.
- iPhone 14 (iOS 16.0.1, build 20A371): Crash Detection's alarm, repeated 'whoops' countdown and looped spoken emergency message, plus the optional Power On & Off Sounds chime (iPhone 14-only at introduction, later extended to iPhone 15/16/17). General devices got 16.0 (20A362). https://support.apple.com/en-us/104959 , https://www.macrumors.com/2022/09/07/iphone-14-mac-like-startup-sound/
- iPhone 15 / 15 Pro (iOS 17.0, builds 21A326 / 21A327): out-of-box builds distinct from the 21A329 image pushed to existing devices on 18 September 2023.
- iPhone 16 line (iOS 18.0): Audio Mix in Photos, hardware-gated to the iPhone 16 four-microphone array. iOS 26 opened the API to third-party apps but still only on iPhone 16 and newer. https://www.macrumors.com/how-to/iphone-16-edit-spatial-audio-in-video-audio-mix/
- iPhone 16e (iOS 18.3 build 22D8063 and 18.3.1 build 22D8075): the only device on those builds; general devices got 22D63 and 22D72. The 22D8075-vs-22D72 pair is the best available like-for-like device diff.
- iPhone 17 / 17 Pro / iPhone Air (iOS 26.0, preinstall builds 23A330 and 23A345): distinct from the general 26.0 build 23A341. No audio difference is documented - specifically, no new or changed camera shutter sound was found for the new Center Stage front camera.

## What this research could not establish

- The best primary source was unreachable for the entire research window. theiphonewiki.com returned HTTP 502 and theapplewiki.com returned HTTP 403 to every researcher who tried, across multiple slices and both WebFetch and curl. That site's Tones article and build tables are the only known public source for exact per-version tone-file diffs and a definitive list of device-exclusive build IDs. Everything here about which files changed is inferred from press coverage, not from a file list. Re-run those lookups when the site is back up.
- Six of eight researchers exhausted their web-search quota mid-task. Every 'no audio change found' should be read as 'not examined', not as a verified negative. The specifically unexamined ranges are: 1.0.x, 1.1.x, 3.0.1, 3.1-3.1.3, 3.2, 4.0.x, 4.1, 5.1, 5.1.1, 6.0.1, 6.1.1-6.1.6; most 12.x and 15.x security-only patches; and exhaustive per-patch checks from 17.3 onward through 18.7.
- No evidence was found of an audio-asset change in any three-component x.y.z release from iOS 12.0 through 26.6. Apple publishes SDK release notes only at x.y granularity, so there is no official changelog to check for any x.y.z patch. This is why the must-have list has two entries rather than the 10-25 requested - the evidence does not support more. The rest of the priority list is device-tree coverage insurance, not documented audio change.
- Researchers disagree on when Siri's deep-learning voice arrived. One slice places the concatenative-to-neural switch at iOS 11.0; another places the deep mixture density network debut at iOS 10.0 with iOS 11.0 being a new-voice-talent refresh. Both cite the same Apple machine learning page (https://machinelearning.apple.com/research/siri-voices). We have not resolved which reading is correct.
- Researchers disagree on where the first siren-class emergency audio lands. One slice attributes the Emergency SOS countdown siren to iOS 11.0 with good sourcing; another raises Wireless Emergency Alerts (WEA/CMAS) around iOS 6.1 but notes the AT&T rollout in June 2013 came via a carrier-settings bundle, not necessarily an OS build. Whether the WEA attention signal is an OS asset or a carrier-bundle asset is unresolved.
- The task brief's premise that iOS 5.0 carried a large tone refresh is not supported. The default-tone-set expansion was iOS 4.2.1 (17 new text tones) and the re-edit was 4.3; iOS 5.0's tone change was infrastructural (iTunes Tone Store). Similarly, the brief's association of a new Siri voice generation with iOS 18 is not supported - 18.0/18.1 shipped a visual redesign around the existing voice, and the new expressive, user-tunable Siri voice is reported for iOS 27.0 (released 2026-09-14), which falls outside the stated 1.0-26.6 scope.
- Siri and VoiceOver voices are commonly delivered as on-demand Mobile Assets after setup rather than baked into the shipping IPSW. A static IPSW extraction may not contain the voices a release nominally adds. This caveat applies to every Siri-voice entry above (13.0, 14.5, 15.4, 26.1) and to VoiceOver's enhanced-quality voices. Supplementing with a live device's downloaded-asset cache may be necessary.
- It is unresolved for several features whether the audio lives in the iOS image or in accessory firmware: the Find My AirPods chirp (10.3), the AirPods Pro 2 hearing-test tones (18.1), AirTag separation beeps (not in iOS at all), and the HomePod setup sounds. These must be settled by inspection, not research.
- Unverified leads that were deliberately not promoted to findings: iOS 11.2.5 as the only mid-cycle patch with a new audio feature (HomePod pairing plus Siri News) - asserted by a researcher with no URL; a Sherwood Forest / Choo Choo ringtone relocation possibly tied to 14.7.1 - Apple Support Community posts only; a NameDrop sound effect in 17.0 - social-media video only, no written press; alarm-tone names (Birdsong, Helios, Orbit, Springtide, Early Riser, First Light, Droplets, Bright-Eyed, Sunny) appearing in 2026 roundups with no source tying them to iOS 26 rather than an earlier Sleep/Bedtime release; and the claim that pre-iOS-11 Siri voices survive under VoiceOver names (Aaron, Nicky, Arthur, Martha, Catherine, Gordon).
- Two entries rest on AppleVis forum threads that could only be read through search-engine snippets because the site returns HTTP 403 to automated fetching: the iOS 17.1 VoiceOver voice-fidelity regression (450 MB to 66 MB) and the iOS 26 observation that legacy system sounds were not redesigned. Both should be verified against actual extracted files.
- Only two audio removals were established, and neither is primary-sourced. The iOS 7.0 unlock-chime removal is sourced to jailbreak-tweak blog coverage; the iOS 9.0 removal of Nike + iPod and its spoken workout prompts is sourced to Apple Support Community and forum threads. No removal at all could be substantiated for iOS 12.0-15.8 or for any 26.x release.
- Candidate removals named in the brief that turned up no citable audio evidence and should be treated as open: Newsstand to News, iTunes Ping, Passbook to Wallet, Game Center sound changes, Home app sounds, Apple Watch pairing audio, and deprecated Siri/VoiceOver languages or language packs. Voice Control was never removed - it persists as an Accessibility feature.
- The structural history of the UISounds directory itself (subfolder additions, reorganisations, path changes across versions) could not be established from any web source. This is a filesystem fact that should be answered by diffing directory listings across extracted images rather than by more research.
- Several build IDs in the timeline are absent, and those present come from Wikipedia and IPSW mirrors rather than from Apple. The exclusivity claims for 17E8258 (iPhone SE 2), 22D8063 / 22D8075 (iPhone 16e) and 14A403 (iPhone 7) were cross-checked against mirror listings but not against an authoritative build table, because the authoritative source was down. Verify before relying on them.
- Classic device-exclusive build candidates were never checked at all because the relevant wiki was down: iPhone 4S (9A406), iPhone 6 / 6 Plus (12A405), and the full iPhone X 11.1 / 11.2 build lineage.
