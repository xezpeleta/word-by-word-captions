#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 sts=4 et :

"""
This script will generate a video with word-level timestamps captions.

If a video is provided, it will be used as the base video. If not, a blank
video will be generated with black background and white text.

The word-level timestamps captions are provided in a JSON file. Currently, the
WhisperX generated JSON file is supported.

How does it work?
The script will generate HTML-styled SRT subtitles with precise word-level timing
Then, `ffmpeg` is used to burn the subtitles onto the video.

Usage:
    wltvideo.py -h
    wltvideo.py -v <video> -j <json> -o <output>
"""

import json
import argparse
from datetime import timedelta
import os
import tempfile
import subprocess
import sys


def format_timestamp(seconds):
    """Convert seconds to SRT format: HH:MM:SS,mmm"""
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    seconds_int = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds_int:02d},{milliseconds:03d}"


def split_text(text, max_chars):
    """Split text into lines respecting word boundaries and max characters per line"""
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        word_length = len(word)
        # Add +1 for the space between words
        if current_length + word_length + (1 if current_line else 0) <= max_chars:
            current_line.append(word)
            current_length += word_length + (1 if current_line else 0)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
            current_length = word_length
    
    if current_line:
        lines.append(" ".join(current_line))
    return lines

def preprocess_json_data(json_data, max_lines=None, max_line_chars=None):
    """Preprocess JSON data to split segments according to line limits"""
    if not max_lines and not max_line_chars:
        return json_data

    new_segments = []
    
    for segment in json_data.get('segments', []):
        words = segment.get('words', [])
        if not words:
            continue

        # Get the full text and split it if needed
        remaining_words = words.copy()
        while remaining_words:
            # Build text from remaining words
            text = "".join([word.get('word', '') + ' ' for word in remaining_words]).strip()
            
            # Split into lines if needed
            if max_line_chars:
                lines = split_text(text, max_line_chars)
                if max_lines:
                    lines = lines[:max_lines]
            else:
                lines = [text]

            # Process first line
            line = lines[0]
            line_words = []
            line_start = None
            line_end = None
            
            # Find words that belong to this line
            i = 0
            remaining_line = line
            while i < len(remaining_words) and remaining_line:
                word = remaining_words[i]
                word_text = word.get('word', '').strip()
                
                if word_text and word_text in remaining_line:
                    if line_start is None:
                        line_start = word.get('start', 0)
                    line_end = word.get('end', 0)
                    line_words.append(word)
                    # Remove the word from the line text we're searching
                    remaining_line = remaining_line.replace(word_text, '', 1).lstrip()
                    i += 1
                else:
                    break
            
            # Create new segment for this line
            if line_words:
                new_segment = {
                    'start': line_start,
                    'end': line_end,
                    'words': line_words
                }
                new_segments.append(new_segment)
                # Remove processed words from remaining_words
                remaining_words = remaining_words[len(line_words):]
            else:
                # Safety check - if we couldn't process any words, break to avoid infinite loop
                break

    return {'segments': new_segments}

def generate_srt_file(json_data, max_lines=None, max_line_chars=None):
    """Generate an SRT subtitle file with HTML styling for word-level highlighting"""
    # Preprocess JSON data according to line limits
    processed_json = preprocess_json_data(json_data, max_lines, max_line_chars)
    
    srt_content = ""
    subtitle_index = 1
    
    for segment in processed_json.get('segments', []):
        segment_start = segment.get('start', 0)
        segment_end = segment.get('end', 0)
        words = segment.get('words', [])
        
        if not words:
            continue
            
        # Create the full text of the segment
        full_text = "".join([word.get('word', '') + ' ' for word in words]).strip()
        
        # Keep track of the current position in the text
        current_pos = 0
        
        # For each word, create a subtitle spanning from its start time to the next word's start time
        for i, word in enumerate(words):
            word_text = word.get('word', '')
            word_start = word.get('start', 0)
            # If this is the last word, use segment end time, otherwise use next word's start time
            word_end = segment_end if i == len(words) - 1 else words[i + 1].get('start', 0)
            
            # Find the next occurrence of the word starting from current_pos
            word_pos = full_text.find(word_text.strip(), current_pos)
            if word_pos >= 0:
                # Create text with the current word highlighted in yellow
                highlighted_text = (
                    full_text[:word_pos] +
                    f'<font color="yellow">{word_text.strip()}</font>' +
                    full_text[word_pos + len(word_text.strip()):]
                )
                
                # Update current position to after this word
                current_pos = word_pos + len(word_text.strip())
                
                # Format the SRT entry for the highlighted word
                srt_content += f"{subtitle_index}\n"
                srt_content += f"{format_timestamp(word_start)} --> {format_timestamp(word_end)}\n"
                srt_content += f"{highlighted_text}\n\n"
                subtitle_index += 1
            
    # Write SRT content to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.srt', mode='w', encoding='utf-8') as f:
        f.write(srt_content)
        srt_file = f.name
    
    return srt_file


def create_blank_video(duration, output_path):
    """Create a blank video with the specified duration"""
    cmd = [
        'ffmpeg', '-y',
        '-f', 'lavfi', '-i', f'color=c=black:s=1280x720:d={duration}',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating blank video: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--video', help='Input video file')
    parser.add_argument('-j', '--json', help='Input JSON file', required=True)
    parser.add_argument('-o', '--output', help='Output video file', required=True)
    parser.add_argument('--max_lines', type=int, help='Maximum number of lines per subtitle', default=1)
    parser.add_argument('--max_line_chars', type=int, help='Maximum characters per line', default=40)
    args = parser.parse_args()

    # Read JSON
    with open(args.json) as f:
        json_data = json.load(f)

    # Generate SRT file with HTML styling for word-level highlighting
    srt_file = generate_srt_file(json_data, args.max_lines, args.max_line_chars)
    
    # Calculate the total duration of the video from JSON data
    total_duration = 0
    for segment in json_data.get('segments', []):
        if segment.get('end', 0) > total_duration:
            total_duration = segment.get('end', 0)
    
    # Add some padding to the end
    total_duration += 2  # Add 2 seconds
    
    # Use ffmpeg to burn the subtitles onto the video
    if args.video:
        input_video = args.video
    else:
        # Create a blank video with appropriate duration
        temp_video = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
        if not create_blank_video(total_duration, temp_video):
            print("Failed to create blank video", file=sys.stderr)
            sys.exit(1)
        input_video = temp_video
    
    # Burn subtitles onto the video using the SRT file
    cmd = [
        'ffmpeg', '-y',
        '-i', input_video,
        '-vf', f'subtitles={srt_file}:force_style=\'FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=1,Shadow=1,MarginV=20\'',
        '-c:a', 'copy',
        args.output
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Video with karaoke subtitles created: {args.output}")
    except subprocess.CalledProcessError as e:
        print(f"Error burning subtitles: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Clean up temporary files
    try:
        os.remove(srt_file)
        if not args.video:
            os.remove(input_video)
    except OSError:
        pass


if __name__ == '__main__':
    main()
