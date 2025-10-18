"""
Data loading functions for different NDJSON formats.
"""

import json
import pandas as pd
from typing import Dict, List


def load_old_format_scores(file_path: str) -> pd.DataFrame:
    """
    Load old format NDJSON data with schema:
    {"provider":"AWS","service_name":"AmazonNeptune","gemini_1_5_pro_score":6.21,"service_alias":"Amazon Neptune","gemini_2_0_flash_score":6.29}
    
    Creates an "avg_gemini_score" column if both gemini scores are present.
    
    Args:
        file_path: Path to the NDJSON file
        
    Returns:
        DataFrame with loaded and processed score data
    """
    data = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    df = pd.DataFrame(data)
    
    # Clean up score columns
    score_columns = ['gemini_1_5_pro_score', 'gemini_2_0_flash_score', 'score']
    for col in score_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Create avg_gemini_score if both gemini scores exist
    if 'gemini_1_5_pro_score' in df.columns and 'gemini_2_0_flash_score' in df.columns:
        df['avg_gemini_score'] = df[['gemini_1_5_pro_score', 'gemini_2_0_flash_score']].mean(axis=1)
    elif 'score' in df.columns:
        # If there's already a 'score' column, rename it to avg_gemini_score
        df['avg_gemini_score'] = df['score']
    
    return df


def load_new_format_scores(file_path: str) -> pd.DataFrame:
    """
    Load new format NDJSON data with schema:
    {"provider": "AWS", "service_name": "AWSDirectConnect", "claude_3.5_score": 2.14, "service_alias": "AWS Direct Connect"}
    
    Automatically detects score columns that end with '_score'.
    
    Args:
        file_path: Path to the NDJSON file
        
    Returns:
        DataFrame with loaded and processed score data
    """
    data = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    df = pd.DataFrame(data)
    
    # Find and clean all score columns (ending with '_score')
    score_columns = [col for col in df.columns if col.endswith('_score')]
    for col in score_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df
