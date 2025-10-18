import json
import sys
import argparse

def extract_services(input_file: str, output_file: str):
    """
    Extract provider, service_name, and service_alias from cei_scores.ndjson
    Output one line per service with only those three fields.
    """
    
    extracted_count = 0
    
    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line_num, line in enumerate(infile, 1):
            if line.strip():
                try:
                    data = json.loads(line)
                    
                    # Extract only the three required fields
                    extracted = {
                        "provider": data.get("provider", ""),
                        "service_name": data.get("service_name", ""), 
                        "service_alias": data.get("service_alias", data.get("service_name", ""))
                    }
                    
                    # Write to output file
                    outfile.write(json.dumps(extracted) + '\n')
                    extracted_count += 1
                    
                except json.JSONDecodeError:
                    print(f"Warning: Skipping invalid JSON at line {line_num}")
                    continue
    
    print(f"Extraction complete. {extracted_count} services extracted to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract provider, service_name, and service_alias from cei_scores.ndjson",
        epilog="Example: python extract_services.py --input cei_scores.ndjson --output extracted_services.ndjson"
    )
    
    parser.add_argument('--input', required=True, help='Input NDJSON file path')
    parser.add_argument('--output', required=True, help='Output NDJSON file path')
    
    args = parser.parse_args()
    
    extract_services(args.input, args.output)