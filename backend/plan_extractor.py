import json
import csv

def get_char_value(characteristics, char_name):
    for char in characteristics:
        if char.get('name') == char_name:
            # Check if characteristicValues is a list and not empty
            values = char.get('characteristicValues')
            if isinstance(values, list) and values:
                return values[0].get('value', '')
    return ''

def extract_plan_data(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    plans = []
    print("Starting plan extraction...")
    for i, offering in enumerate(data.get('salesOfferings', [])):
        po = offering.get('productOffering')
        if not po or po.get('group') != 'tariff':
            continue

        name = po.get('name', f'Unknown Plan {i}')
        print(f"\nProcessing offering {i}: {name}")

        # --- Price Extraction ---
        price = 0.0
        price_list = po.get('productOfferingPrices')
        if price_list and isinstance(price_list, list):
            for price_item in price_list:
                if price_item.get('priceType') == 'recurringFee' and 'monthly' in price_item.get('name', '').lower():
                    price_info = price_item.get('price')
                    if price_info and isinstance(price_info, dict):
                        price = price_info.get('taxIncludedAmount', 0.0)
                        print(f"  Found recurring price: {price}")
                        break
        
        if price <= 0:
            print("  Skipping plan: No valid recurring price found.")
            continue

        # --- Attribute Extraction ---
        plan_id = po.get('id', '')
        characteristics = po.get('characteristics', [])
        description = po.get('description', '').lower()
        
        data_volume = get_char_value(characteristics, 'Data')

        # --- Feature Extraction ---
        features = []
        if 'eu' in description or 'roaming' in description:
            features.append('EU roaming')
        if '5g' in name.lower() or '5g' in po.get('shortDescription', '').lower():
            features.append('5G')
        if 'hotspot flat' in description:
            features.append('HotSpot Flat')
        if any(c.get('label') == 'VoLTE und WLAN Call' for c in characteristics):
            features.append('VoLTE')
            features.append('Wi-Fi Calling')
        if 'cashback' in description:
            features.append('Cashback')
        if 'streamon' in description:
            features.append('StreamOn')

        print(f"  Extracted data: ID={plan_id}, Price={price}, Data={data_volume}")

        plans.append({
            'id': plan_id,
            'name': name,
            'price': price,
            'duration': 'monthly',
            'data': f"{data_volume}GB",
            'minutes': 'unlimited',
            'sms': 'unlimited',
            'features': ';'.join(features),
            'popular': True
        })

    print(f"\nExtraction complete. Found {len(plans)} valid plans.")
    return plans

def write_to_csv(plans, csv_file):
    if not plans:
        print("No plans to write.")
        return

    fieldnames = ['id', 'name', 'price', 'duration', 'data', 'minutes', 'sms', 'features', 'popular']
    
    # Append to the CSV file instead of overwriting
    try:
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            # Write header only if the file is new/empty
            if f.tell() == 0:
                writer.writeheader()
            writer.writerows(plans)
    except IOError as e:
        print(f"Error writing to {csv_file}: {e}")

if __name__ == '__main__':
    extracted_plans = extract_plan_data('tariff 1.json')
    if extracted_plans:
        output_csv = 'sample_plans.csv'
        write_to_csv(extracted_plans, output_csv)
        print(f"Appended {len(extracted_plans)} plans to {output_csv}")
