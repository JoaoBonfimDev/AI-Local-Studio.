"""Shared sequential render path, derived from Gameplay 0.3 and Shorts 1.1.

H.264/PCM NUT intermediates -> video stream copy + single AAC encode -> MP4.
Never concatenate independently primed AAC clips. Final files are atomic.
"""
from fractions import Fraction
import json
import math
from pathlib import Path
import shutil

from core.cache import key,fingerprint
from core.gpu import nvenc_available
from core.media import ffmpeg,probe
from core.process import save_json,load_json
from core.naming import video_stem,unique_video
from legacy.gameplay_editor.render import QUALITY_PRESETS
from legacy.aishorts.render import ass_time,ass_text,caption_groups
from .audio import segment_filter,final_filter
from .validation import validate


def encoder_args(encoder,quality):
    profile=QUALITY_PRESETS[quality]
    if encoder=='h264_nvenc':
        return ['-c:v',encoder,'-preset',profile['nvenc_preset'],'-tune','hq','-rc','vbr','-cq',str(profile['cq']),'-b:v','0']
    return ['-c:v','libx264','-preset',profile['cpu_preset'],'-crf',str(profile['crf']),'-threads','4']


def compatible_color_filter(video):
    """Convert full-range samples, rather than merely relabeling their metadata.

    H.264 VUI full_range can make FFprobe report yuvj420p even when the
    encoder was given -pix_fmt yuv420p. Windows exports use limited-range
    samples AND matching bitstream metadata, preserving displayed colors.
    """
    full=video.get('color_range')=='pc' or str(video.get('pix_fmt','')).startswith('yuvj')
    input_range='pc' if full else 'auto'
    return f'scale=iw:ih:in_range={input_range}:out_range=tv,format=yuv420p,setparams=range=limited'


def captions(path,segments,start,end):
    header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Arial,58,&H00FFFFFF,&H00FFFFFF,&H00202020,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,65,65,370,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    rows=[]
    for group in caption_groups(segments):
        a=max(start,group[0]['start']);b=min(end,group[-1]['end'])
        if b>a:
            rows.append(f"Dialogue: 0,{ass_time(a-start)},{ass_time(b-start)},Caption,,0,0,0,,{ass_text(' '.join(w['text'].strip() for w in group))}")
    Path(path).write_text(header+'\n'.join(rows),encoding='utf-8-sig')


def render(source,info,plan,settings,folder,runner,segments=None,on_encoder=None):
    from modes.plan import validate as validate_plan
    validate_plan(plan,info['duration'],settings['mode'])
    folder=Path(folder)
    if fingerprint(source)!=settings['source_identity']:raise ValueError('O arquivo original mudou. Analise novamente.')
    fps=Fraction(info['fps']);fps_float=float(fps)
    if not 0<fps_float<=1000:raise ValueError('FPS da fonte inválido.')
    dimensions=[1080,1920] if settings['mode']=='shorts' else [math.ceil(info['width']/2)*2,math.ceil(info['height']/2)*2]
    signature=key([plan,settings['quality'],settings['encoder'],settings['captions'],settings['render_audio_track'],dimensions,
        settings.get('game_name',''),settings.get('export_directory',''),'render-2.0.6-named-exports'])
    work=folder/'.render'/signature
    work.mkdir(parents=True,exist_ok=True)
    if settings['encoder']=='cpu':encoder='libx264'
    else:
        encoder='h264_nvenc' if nvenc_available(runner) else 'libx264'
        if encoder=='libx264' and settings['encoder']=='nvenc':raise RuntimeError('NVENC indisponível; selecione Automático ou CPU.')
    # A run uses the same encoder for all parts, even after a resume.
    saved_encoder=work/'encoder.json'
    if saved_encoder.exists():encoder=load_json(saved_encoder)['encoder']
    save_json(saved_encoder,dict(encoder=encoder))
    if settings['encoder']=='nvenc' and encoder!='h264_nvenc':raise RuntimeError('A renderização exige GPU NVENC; o Studio não utilizará CPU neste modo.')
    if on_encoder:on_encoder(encoder)
    destination=Path(settings.get('export_directory') or folder)
    destination.mkdir(parents=True,exist_ok=True)
    named=bool(settings.get('game_name'))
    names_file=work/'destinations.json'
    names=load_json(names_file) if names_file.is_file() else {}
    outputs=[]
    for episode in plan['episodes']:
        runner.check()
        number=str(episode['number'])
        if number not in names:
            target=unique_video(destination,video_stem(settings,episode['number'])) if named else destination/f"{settings['mode']}_{episode['number']:02}_{signature[:8]}.mp4"
            names[number]=str(target.resolve());save_json(names_file,names)
        final=Path(names[number])
        # Only this work's recorded targets can be reused; unrelated pre-existing files
        # are skipped by unique_video, never overwritten or accepted as our export.
        if final.resolve().parent!=destination.resolve():raise ValueError('Destino de exportação fora da pasta autorizada.')
        report_path=work/f'validation_{episode["number"]:02}.json' if settings.get('export_directory') else final.with_suffix('.validation.json')
        audio_indices=[settings['render_audio_track']] if settings['mode']=='shorts' and info['audio'] else list(range(len(info['audio'])))
        parts=[];lengths=[]
        for i,row in enumerate(episode['segments']):
            runner.check()
            start=round(row['start']*fps_float)/fps_float
            frames=max(1,round((row['end']-row['start'])*fps_float))
            duration=frames/fps_float
            if start+duration>info['duration']+1/fps_float:raise ValueError('Corte ultrapassa o final da fonte após alinhamento de quadros.')
            part=work/f"e{episode['number']:02}_p{i:05}.nut"
            marker=part.with_suffix('.json')
            expected=dict(duration=duration,dimensions=dimensions,audio_tracks=len(audio_indices),fps_float=fps_float)
            # Revalidate finished outputs on resume; user edits are never trusted by filename.
            if not (part.exists() and marker.exists() and load_json(marker).get('bytes')==part.stat().st_size):
                partial=part.with_suffix('.partial.nut')
                vf='setpts=PTS-STARTPTS,'+compatible_color_filter(info['video'])
                if settings['mode']=='shorts':
                    vf+=(',split=2[bg0][fg0];[bg0]scale=304:540:force_original_aspect_ratio=increase,crop=304:540,gblur=sigma=18,eq=brightness=-0.16:saturation=0.7,scale=1080:1920[bg];'
                         '[fg0]scale=1080:608:force_original_aspect_ratio=decrease,pad=1080:608:(ow-iw)/2:(oh-ih)/2[fg];[bg][fg]overlay=0:650,setsar=1')
                    if settings['captions']:
                        captions(work/'captions.ass',segments or [],start,start+duration)
                        vf+=',ass=captions.ass'
                elif info['width']%2 or info['height']%2:
                    vf+=',pad=ceil(iw/2)*2:ceil(ih/2)*2'
                command=ffmpeg()+['-ss',f'{start:.9f}','-i',str(source),'-t',f'{duration:.9f}','-map','0:v:0']
                for index in audio_indices:command+=['-map',f'0:a:{index}']
                command+=['-filter_complex_threads','1','-vf',vf,*encoder_args(encoder,settings['quality']),'-pix_fmt','yuv420p','-color_range','tv','-r',str(fps),'-fps_mode','cfr','-map_chapters','-1','-map_metadata','-1']
                if audio_indices:
                    command+=['-c:a','pcm_f32le','-ar','48000','-af',segment_filter(duration)]
                else:command+=['-an']
                command+=[str(partial)]
                try:
                    runner.run(command,total=duration,stage=f"Episódio {episode['number']}: corte {i+1}/{len(episode['segments'])}",cwd=work)
                except RuntimeError:
                    if encoder=='h264_nvenc' and settings['encoder']=='auto':
                        # Different codecs/settings must not be silently mixed on concat.
                        for previous in work.glob('*.nut'):previous.unlink()
                        for previous in work.glob('e*_p*.json'):previous.unlink()
                        save_json(saved_encoder,dict(encoder='libx264'))
                        runner.report('Fallback CPU',0,1,'NVENC falhou; reiniciando os intermediários na CPU.')
                        return render(source,info,plan,settings,folder,runner,segments,on_encoder)
                    raise
                partial.replace(part)
                save_json(marker,dict(bytes=part.stat().st_size,duration=duration))
            else:
                runner.report('Corte em checkpoint',duration,duration,f"Corte {i+1} recuperado")
            parts.append(part);lengths.append(duration)
        expected=dict(duration=sum(lengths),dimensions=dimensions,audio_tracks=len(audio_indices),fps_float=fps_float)
        if final.exists():
            report=validate(final,expected,runner)
            save_json(report_path,report);outputs.append(report);continue
        listing=work/'concat.txt'
        listing.write_text(''.join(f"file '{p.name}'\nduration {length:.12f}\n" for p,length in zip(parts,lengths)),encoding='utf-8')
        pending=work/'final.partial.mp4'
        command=ffmpeg()+['-f','concat','-safe','1','-i','concat.txt','-map','0:v:0','-map','0:a?','-c:v','copy']
        if audio_indices:
            command+=['-c:a','aac','-profile:a','aac_low','-b:a',QUALITY_PRESETS[settings['quality']]['audio'],'-af',final_filter()]
        command+=['-t',f"{expected['duration']:.9f}",'-map_metadata','-1','-movflags','+faststart',str(pending)]
        runner.run(command,total=expected['duration'],stage=f"Finalização MP4 {episode['number']}",cwd=work)
        report=validate(pending,expected,runner)
        if final.exists():raise FileExistsError('A saída já existe; não será substituída.')
        # No file is exposed as complete before full validation.
        pending.rename(final);report['file']=str(final)
        save_json(report_path,report);outputs.append(report)
        # Completed clips can be regenerated; retain only interrupted episode parts.
        for part in parts:
            part.unlink(missing_ok=True);part.with_suffix('.json').unlink(missing_ok=True)
    save_json(folder/'resultado.json',dict(files=outputs,encoder=encoder,source=settings['source_identity']))
    return outputs,encoder
