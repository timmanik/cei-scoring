"""
Data loading functions for different NDJSON formats.
"""

import json
import pandas as pd
from typing import Dict, List, Tuple


def load_old_format_scores(file_path: str, run_identifier: str = None) -> pd.DataFrame:
    """
    Load old format NDJSON data with schema:
    {"provider":"AWS","service_name":"AmazonNeptune","gemini_1_5_pro_score":6.21,"service_alias":"Amazon Neptune","gemini_2_0_flash_score":6.29}
    
    Creates an "avg_gemini_score" column if both gemini scores are present.
    
    Args:
        file_path: Path to the NDJSON file
        run_identifier: Optional identifier to distinguish different runs (e.g., "baseline", "updated")
        
    Returns:
        DataFrame with loaded and processed score data
    """
    import os
    
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
    
    # If run_identifier is provided, rename score columns to include it
    if run_identifier:
        rename_dict = {}
        for col in score_columns:
            if col in df.columns:
                if col == 'score':
                    new_name = f"score_{run_identifier}"
                else:
                    base_name = col[:-6]  # Remove '_score'
                    new_name = f"{base_name}_{run_identifier}_score"
                rename_dict[col] = new_name
        df.rename(columns=rename_dict, inplace=True)
        
        # Update score_columns list for avg calculation
        score_columns = [rename_dict.get(col, col) for col in score_columns if col in df.columns]
    
    # Create avg_gemini_score if both gemini scores exist
    gemini_cols = [col for col in df.columns if 'gemini' in col and 'score' in col]
    if len(gemini_cols) >= 2:
        avg_col_name = f"avg_gemini_{run_identifier}_score" if run_identifier else "avg_gemini_score"
        df[avg_col_name] = df[gemini_cols].mean(axis=1)
    elif any('score' in col for col in df.columns):
        # If there's a single score column, use it as avg
        score_col = next(col for col in df.columns if 'score' in col)
        avg_col_name = f"avg_gemini_{run_identifier}_score" if run_identifier else "avg_gemini_score"
        df[avg_col_name] = df[score_col]
    
    return df


def load_multiple_score_files(file_configs: List[Tuple[str, str, str]]) -> List[pd.DataFrame]:
    """
    Load multiple score files with run identifiers to distinguish different runs.
    
    Args:
        file_configs: List of tuples (file_path, format_type, run_identifier)
                     format_type should be either 'old' or 'new'
                     run_identifier is a string to distinguish this run (e.g., 'with_tools', 'without_tools')
    
    Returns:
        List of DataFrames with properly labeled score columns
    
    Example:
        file_configs = [
            ('../results/scores/2025-10-18-19-50-26-llama-3-3-70b.ndjson', 'new', 'with_tools'),
            ('../results/scores/2025-10-23-15-23-13-llama-3-3-70b.ndjson', 'new', 'without_tools')
        ]
        dataframes = load_multiple_score_files(file_configs)
    """
    dataframes = []
    
    for file_path, format_type, run_identifier in file_configs:
        try:
            if format_type.lower() == 'old':
                df = load_old_format_scores(file_path, run_identifier)
            elif format_type.lower() == 'new':
                df = load_new_format_scores(file_path, run_identifier)
            else:
                print(f"Warning: Unknown format_type '{format_type}' for {file_path}. Skipping.")
                continue
            
            print(f"Loaded {file_path} ({format_type} format) with identifier '{run_identifier}':")
            print(f"  - {len(df)} services")
            score_cols = [col for col in df.columns if 'score' in col.lower()]
            print(f"  - Score columns: {score_cols}")
            
            dataframes.append(df)
            
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    
    return dataframes


def load_new_format_scores(file_path: str, run_identifier: str = None) -> pd.DataFrame:
    """
    Load new format NDJSON data with schema:
    {"provider": "AWS", "service_name": "AWSDirectConnect", "claude_3.5_score": 2.14, "service_alias": "AWS Direct Connect"}
    
    Automatically detects score columns that end with '_score' and optionally adds run identifier to column names.
    
    Args:
        file_path: Path to the NDJSON file
        run_identifier: Optional identifier to distinguish different runs (e.g., "with_tools", "without_tools")
        
    Returns:
        DataFrame with loaded and processed score data
    """
    import os
    
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
    
    # If run_identifier is provided, rename score columns to include it
    if run_identifier:
        rename_dict = {}
        for col in score_columns:
            # Remove '_score' suffix, add run identifier, then add '_score' back
            base_name = col[:-6]  # Remove '_score'
            new_name = f"{base_name}_{run_identifier}_score"
            rename_dict[col] = new_name
        df.rename(columns=rename_dict, inplace=True)
    else:
        # If no run_identifier provided, try to extract from filename
        filename = os.path.basename(file_path)
        if filename.endswith('.ndjson'):
            # Extract timestamp or other identifier from filename
            # e.g., "2025-10-18-19-50-26-llama-3-3-70b.ndjson" -> "2025-10-18-19-50-26"
            parts = filename[:-7].split('-')  # Remove .ndjson and split by -
            if len(parts) >= 5:  # Has timestamp format
                timestamp = '-'.join(parts[:5])  # First 5 parts are the timestamp
                rename_dict = {}
                for col in score_columns:
                    base_name = col[:-6]  # Remove '_score'
                    new_name = f"{base_name}_{timestamp}_score"
                    rename_dict[col] = new_name
                df.rename(columns=rename_dict, inplace=True)
    
    return df
