"""
Score comparison functions for cross-model analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, List


def compare_model_scores_unified(dataframes: List[pd.DataFrame], 
                                disagreement_threshold: float = 2.0,
                                show_similar: bool = False,
                                similarity_threshold: float = 0.5,
                                columns_to_compare: List[str] = None) -> Dict:
    """
    Unified function to compare scores across multiple models/dataframes.
    
    Args:
        dataframes: List of pandas DataFrames with score data
        disagreement_threshold: Threshold for flagging high disagreement (default: 2.0)
        show_similar: Whether to include services with high similarity (default: False)
        similarity_threshold: Threshold for high similarity (default: 0.5)
        columns_to_compare: Specific list of score column names to compare (default: None, uses all)
    
    Returns:
        Dictionary with flagged services and analysis results
    """
    
    # Combine all dataframes and identify score columns
    all_score_columns = []
    combined_data = []
    
    for i, df in enumerate(dataframes):
        # Find score columns in this dataframe
        score_cols = [col for col in df.columns if 'score' in col.lower()]
        all_score_columns.extend(score_cols)
        
        # Add dataframe identifier
        df_copy = df.copy()
        df_copy['dataframe_id'] = i
        combined_data.append(df_copy)
    
    # Get unique score columns across all dataframes
    unique_score_columns = list(set(all_score_columns))
    
    # Filter to only the specified columns if provided
    if columns_to_compare is not None:
        # Validate that the specified columns exist in the data
        available_columns = [col for col in columns_to_compare if col in unique_score_columns]
        if not available_columns:
            return {"error": f"None of the specified columns {columns_to_compare} found in data. Available columns: {unique_score_columns}"}
        if len(available_columns) != len(columns_to_compare):
            missing_columns = [col for col in columns_to_compare if col not in unique_score_columns]
            print(f"Warning: Some specified columns not found: {missing_columns}")
        unique_score_columns = available_columns
    
    if len(unique_score_columns) < 2:
        return {"error": "Need at least 2 score columns across all dataframes for comparison"}
    
    # Merge dataframes on service_name and provider
    merged_df = pd.DataFrame()
    for df in combined_data:
        if merged_df.empty:
            merged_df = df[['service_name', 'provider', 'service_alias'] + 
                          [col for col in unique_score_columns if col in df.columns]]
        else:
            merge_cols = ['service_name', 'provider']
            score_cols_in_df = [col for col in unique_score_columns if col in df.columns]
            df_subset = df[merge_cols + ['service_alias'] + score_cols_in_df]
            merged_df = merged_df.merge(df_subset, on=merge_cols, how='outer', suffixes=('', '_dup'))
            
            # Handle duplicate service_alias columns
            if 'service_alias_dup' in merged_df.columns:
                merged_df['service_alias'] = merged_df['service_alias'].fillna(merged_df['service_alias_dup'])
                merged_df.drop('service_alias_dup', axis=1, inplace=True)
    
    # Calculate median score and deviations for each service
    results = {
        'disagreement_threshold': disagreement_threshold,
        'similarity_threshold': similarity_threshold,
        'score_columns_analyzed': unique_score_columns,
        'high_disagreement_services': [],
        'high_similarity_services': [],
        'analysis_summary': {}
    }
    
    disagreement_services = []
    similarity_services = []
    
    for _, row in merged_df.iterrows():
        service_name = row['service_name']
        provider = row['provider']
        service_alias = row.get('service_alias', '')
        
        # Get all valid scores for this service
        scores = []
        score_details = {}
        
        for col in unique_score_columns:
            if col in row and pd.notna(row[col]):
                scores.append(row[col])
                score_details[col] = row[col]
        
        if len(scores) < 2:
            continue  # Need at least 2 scores to compare
        
        # Calculate median and deviations
        median_score = np.median(scores)
        deviations = [abs(score - median_score) for score in scores]
        max_deviation = max(deviations)
        
        service_info = {
            'service_name': service_name,
            'provider': provider,
            'service_alias': service_alias,
            'median_score': median_score,
            'max_deviation': max_deviation,
            'scores': score_details,
            'deviations': {col: abs(score_details[col] - median_score) 
                          for col in score_details.keys()}
        }
        
        # Flag high disagreement
        if max_deviation > disagreement_threshold:
            disagreement_services.append(service_info)
        
        # Flag high similarity (if requested)
        if show_similar and max_deviation <= similarity_threshold:
            similarity_services.append(service_info)
    
    # Sort by disagreement level (descending) and similarity level (ascending)
    disagreement_services.sort(key=lambda x: x['max_deviation'], reverse=True)
    similarity_services.sort(key=lambda x: x['max_deviation'])
    
    results['high_disagreement_services'] = disagreement_services
    results['high_similarity_services'] = similarity_services
    
    # Analysis summary
    results['analysis_summary'] = {
        'total_services_compared': len(merged_df),
        'services_with_high_disagreement': len(disagreement_services),
        'services_with_high_similarity': len(similarity_services) if show_similar else 'Not calculated',
        'score_columns_found': len(unique_score_columns)
    }
    
    return results
