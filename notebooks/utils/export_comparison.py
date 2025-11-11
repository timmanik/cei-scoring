import datetime
import os


def export_comparison_results_to_file(comparison_results, filename=None):
    """
    Export comparison analysis results to a text file.
    
    Args:
        comparison_results: Results from compare_model_scores_unified()
        filename: Optional filename. If None, generates timestamp-based filename
    
    Returns:
        str: The filename of the exported file
    """
    
    # Create comparisons folder if it doesn't exist
    comparisons_dir = "../results/comparison-reports"
    os.makedirs(comparisons_dir, exist_ok=True)
    
    # Generate filename if not provided
    if filename is None:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"comparison_analysis_{timestamp}.txt"
    
    # Ensure filename is in the comparisons directory
    if not filename.startswith(comparisons_dir):
        filename = os.path.join(comparisons_dir, filename)
    
    # Check for errors
    if 'error' in comparison_results:
        print(f"❌ Cannot export: {comparison_results['error']}")
        return None
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            # Write header
            f.write("="*80 + "\n")
            f.write("CLOUD SERVICE SCORING COMPARISON ANALYSIS REPORT\n")
            f.write("="*80 + "\n")
            f.write(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Write analysis summary
            f.write("=== ANALYSIS SUMMARY ===\n")
            summary = comparison_results['analysis_summary']
            f.write(f"Total services compared: {summary['total_services_compared']}\n")
            f.write(f"Score columns analyzed: {', '.join(comparison_results['score_columns_analyzed'])}\n")
            f.write(f"Services with high disagreement: {summary['services_with_high_disagreement']}\n")
            f.write(f"Services with high similarity: {summary['services_with_high_similarity']}\n\n")
            
            # Write high disagreement services (ALL services, not just top 10)
            f.write(f"=== HIGH DISAGREEMENT SERVICES (deviation > {comparison_results['disagreement_threshold']}) ===\n")
            f.write(f"Total: {len(comparison_results['high_disagreement_services'])} services\n\n")
            
            for i, service in enumerate(comparison_results['high_disagreement_services'], 1):
                f.write(f"{i}. {service['service_name']} ({service['provider']})\n")
                f.write(f"   Median Score: {service['median_score']:.2f}\n")
                f.write(f"   Max Deviation: {service['max_deviation']:.2f}\n")
                f.write(f"   Scores: {', '.join([f'{k}={v:.2f}' for k, v in service['scores'].items()])}\n")
                f.write(f"   Deviations: {', '.join([f'{k}={v:.2f}' for k, v in service['deviations'].items()])}\n")
                f.write("\n")
            
            # Write high similarity services (ALL services, not just top 5)
            if comparison_results['high_similarity_services']:
                f.write(f"=== HIGH SIMILARITY SERVICES (deviation <= {comparison_results['similarity_threshold']}) ===\n")
                f.write(f"Total: {len(comparison_results['high_similarity_services'])} services\n\n")
                
                for i, service in enumerate(comparison_results['high_similarity_services'], 1):
                    f.write(f"{i}. {service['service_name']} ({service['provider']})\n")
                    f.write(f"   Median Score: {service['median_score']:.2f}\n")
                    f.write(f"   Max Deviation: {service['max_deviation']:.2f}\n")
                    f.write(f"   Scores: {', '.join([f'{k}={v:.2f}' for k, v in service['scores'].items()])}\n")
                    f.write("\n")
            
            # Write footer
            f.write("="*80 + "\n")
            f.write("END OF REPORT\n")
            f.write("="*80 + "\n")
        
        print(f"✅ Comparison results exported to: {filename}")
        print(f"   - High disagreement services: {len(comparison_results['high_disagreement_services'])}")
        if comparison_results['high_similarity_services']:
            print(f"   - High similarity services: {len(comparison_results['high_similarity_services'])}")
        
        return filename
        
    except Exception as e:
        print(f"❌ Error writing to file: {e}")
        return None