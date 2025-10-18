"""
Validation functions for ground truth comparison.
"""

import pandas as pd
from typing import Dict


def validate_dataframe_against_ground_truth(df: pd.DataFrame, ground_truth_data: Dict) -> Dict:
    """
    Validate any dataframe (old or new format) against ground truth data.
    
    Args:
        df: DataFrame with score data (from load_old_format_scores or load_new_format_scores)
        ground_truth_data: Ground truth dictionary with expected ranges
    
    Returns:
        Dictionary with validation results showing services that don't meet ground truth
    """
    
    # Find all score columns in the dataframe
    score_columns = [col for col in df.columns if 'score' in col.lower()]
    
    if not score_columns:
        return {"error": "No score columns found in dataframe"}
    
    results = {
        'score_columns_analyzed': score_columns,
        'total_ground_truth_services': len(ground_truth_data),
        'services_found_in_data': 0,
        'services_outside_range': [],
        'services_within_range': [],
        'services_not_found': [],
        'validation_summary': {}
    }
    
    outside_range_services = []
    within_range_services = []
    not_found_services = []
    
    for service_name, expected in ground_truth_data.items():
        # Find this service in the dataframe
        service_data = df[df['service_name'] == service_name]
        
        if service_data.empty:
            not_found_services.append({
                'service_name': service_name,
                'expected_category': expected['category'],
                'expected_range': expected['expected_range'],
                'provider': expected['provider']
            })
            continue
        
        results['services_found_in_data'] += 1
        service_row = service_data.iloc[0]
        
        # Check each score column against ground truth
        service_validation = {
            'service_name': service_name,
            'provider': expected['provider'],
            'service_alias': service_row.get('service_alias', ''),
            'expected_category': expected['category'],
            'expected_range': expected['expected_range'],
            'scores_analysis': {},
            'any_score_in_range': False,
            'all_scores_in_range': True
        }
        
        for score_col in score_columns:
            if score_col in service_row and pd.notna(service_row[score_col]):
                actual_score = service_row[score_col]
                min_range, max_range = expected['expected_range']
                in_range = min_range <= actual_score <= max_range
                
                service_validation['scores_analysis'][score_col] = {
                    'actual_score': actual_score,
                    'in_range': in_range,
                    'deviation_from_range': 0 if in_range else min(
                        abs(actual_score - min_range), 
                        abs(actual_score - max_range)
                    )
                }
                
                if in_range:
                    service_validation['any_score_in_range'] = True
                else:
                    service_validation['all_scores_in_range'] = False
        
        # Categorize the service based on validation results
        if service_validation['any_score_in_range']:
            within_range_services.append(service_validation)
        else:
            outside_range_services.append(service_validation)
    
    # Sort by deviation (highest deviation first for outside range services)
    outside_range_services.sort(key=lambda x: max(
        [score['deviation_from_range'] for score in x['scores_analysis'].values()]
    ), reverse=True)
    
    results['services_outside_range'] = outside_range_services
    results['services_within_range'] = within_range_services
    results['services_not_found'] = not_found_services
    
    # Summary statistics
    results['validation_summary'] = {
        'total_services_in_ground_truth': len(ground_truth_data),
        'services_found_in_data': results['services_found_in_data'],
        'services_not_found_in_data': len(not_found_services),
        'services_within_expected_range': len(within_range_services),
        'services_outside_expected_range': len(outside_range_services),
        'accuracy_rate': len(within_range_services) / results['services_found_in_data'] if results['services_found_in_data'] > 0 else 0
    }
    
    return results
