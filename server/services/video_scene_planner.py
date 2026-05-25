import math


def plan_scenes(
    subtitle_segments: list[str],
    chunk_durations: list[float],
    images: list[str],
    motion: str = 'slow_zoom_in',
    gap: float = 0.3,
) -> list[dict]:
    if not subtitle_segments or not images:
        return []
    
    total_duration = sum(chunk_durations) + gap * max(0, len(chunk_durations) - 1)
    num_images = len(images)
    
    if num_images == 1:
        return [{
            'index': 1,
            'image': images[0],
            'start': 0.0,
            'end': total_duration,
            'subtitle_start_index': 1,
            'subtitle_end_index': len(subtitle_segments),
            'motion': motion,
            'transition_in': 'fade',
            'transition_out': 'fade',
        }]
    
    scenes = []
    current_time = 0.0
    subs_per_scene = math.ceil(len(subtitle_segments) / num_images)
    
    for i, image in enumerate(images):
        start_sub = i * subs_per_scene
        end_sub = min((i + 1) * subs_per_scene, len(subtitle_segments))
        
        scene_duration = sum(chunk_durations[start_sub:end_sub])
        if end_sub < len(subtitle_segments):
            scene_duration += gap * max(0, end_sub - start_sub - 1)
        
        scenes.append({
            'index': i + 1,
            'image': image,
            'start': round(current_time, 3),
            'end': round(current_time + scene_duration, 3),
            'subtitle_start_index': start_sub + 1,
            'subtitle_end_index': end_sub,
            'motion': motion,
            'transition_in': 'fade' if i > 0 else None,
            'transition_out': 'fade' if i < num_images - 1 else None,
        })
        current_time += scene_duration + gap
    
    return scenes
