# Word-By-Word Captions (wbw-captions)

A Python tool to generate synchronized one-word captions for videos using word-level timestamps from WhisperX.

## Overview

WBW takes WhisperX's word-level timestamp JSON output and creates visually appealing videos with synchronized one-word captions.

The JSON file generated by [WhisperX](https://github.com/m-bain/whisperX) with the high-precision word-level timestamps is required as input.

## Installation

```bash
pip install word-by-word-captions
```

## Dependencies

- ffmpeg (for video processing)

## Usage

### 1. Generate Word-level Timestamps

First, use WhisperX to generate word-level timestamps for your audio/video:

```bash
# Install WhisperX
pip install git+https://github.com/m-bain/whisperX.git

# Generate word-level timestamps
whisperx <audio.wav> --hf_token <your-token> --vad_method silero --language <lang> --model <model> --align_model <align_model>
```

This will create a JSON file with precise word timings.

### 2. Create Captioned Video

```bash
# Add captions to an existing video
wbw-captions --video input_video.mp4 --json whisperx_output.json --output output.mp4
```

Options:
- `-v, --video`: Input video file (optional)
- `-j, --json`: WhisperX JSON output file (required)
- `-o, --output`: Output video file path (required)
- `--max_lines`: Maximum number of lines per subtitle (default: 1)
- `--max_line_chars`: Maximum characters per line (default: 40)

## Example Output

The tool creates videos where:
- Each word is highlighted in yellow as it's spoken
- Words are synchronized with precise timing from WhisperX
- Text is easily readable with proper contrast and outlines
- Captions are positioned at the bottom with proper margins

## Development

To set up the development environment:

1. Clone the repository
2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
3. Run tests:
   ```bash
   pytest
   ```

## License

MIT License
