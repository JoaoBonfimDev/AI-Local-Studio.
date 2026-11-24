"""Normalize only time bases and sample counts; no loudness/music/voice changes."""


def segment_filter(duration, rate=48000):
    # PCM intermediates avoid one AAC priming/padding interval at every cut.
    samples=round(duration*rate)
    return f'asetpts=PTS-STARTPTS,aresample={rate}:async=1:first_pts=0,apad,atrim=end_sample={samples},asetpts=N/SR/TB'


def final_filter():
    return 'aresample=48000:async=1:first_pts=0,asetpts=N/SR/TB'
