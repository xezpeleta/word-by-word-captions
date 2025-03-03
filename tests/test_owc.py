"""Tests for the One-Word-Captions tool"""
import json
import os
import tempfile
import pytest
from owc.owc import (
    format_timestamp,
    split_text,
    preprocess_json_data,
    generate_srt_file,
    create_blank_video
)

def test_format_timestamp():
    assert format_timestamp(3661.5) == "01:01:01,500"
    assert format_timestamp(0.001) == "00:00:00,001"
    assert format_timestamp(360000) == "100:00:00,000"

def test_split_text():
    text = "This is a long sentence that needs to be split"
    assert split_text(text, 10) == ["This is a", "long", "sentence", "that needs", "to be", "split"]
    assert split_text("Short text", 20) == ["Short text"]

def test_preprocess_json_data():
    sample_json = {
        "segments": [{
            "start": 0.0,
            "end": 2.0,
            "words": [
                {"word": "Hello", "start": 0.0, "end": 0.5},
                {"word": "world", "start": 0.5, "end": 1.0}
            ]
        }]
    }
    
    # Test with default settings
    result = preprocess_json_data(sample_json)
    assert len(result["segments"]) == 1
    assert len(result["segments"][0]["words"]) == 2
    
    # Test with max line chars
    result = preprocess_json_data(sample_json, max_line_chars=5)
    assert len(result["segments"]) == 2

def test_generate_srt_file():
    sample_json = {
        "segments": [{
            "start": 0.0,
            "end": 2.0,
            "words": [
                {"word": "Test", "start": 0.0, "end": 0.5},
                {"word": "caption", "start": 0.5, "end": 1.0}
            ]
        }]
    }
    
    srt_file = generate_srt_file(sample_json)
    assert os.path.exists(srt_file)
    with open(srt_file, 'r', encoding='utf-8') as f:
        content = f.read()
        assert "Test" in content
        assert "caption" in content
        assert "<font color=" in content
    os.remove(srt_file)

def test_create_blank_video():
    with tempfile.NamedTemporaryFile(suffix='.mp4') as tmp:
        assert create_blank_video(1.0, tmp.name) == True
        assert os.path.exists(tmp.name)
        assert os.path.getsize(tmp.name) > 0