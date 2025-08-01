import json
import csv
import random

def get_char_value(characteristics, char_name):
    for char in characteristics:
        if char.get('name') == char_name:
            return char.get('value')
    return ''

def extract_device_data(listing_file, num_devices=10):
    with open(listing_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    devices = []
    for offering in data.get('salesOfferings', []):
        if len(devices) >= num_devices:
            break

        po = offering.get('productOffering')
        if not po:
            continue

        # --- Robust Price Extraction ---
        price = 0.0
        price_list = po.get('productOfferingPrice')
        if price_list and isinstance(price_list, list) and len(price_list) > 0:
            price_info = price_list[0].get('price')
            if price_info and isinstance(price_info, dict):
                price = price_info.get('taxIncludedAmount', 0.0)

        # --- Skip if essential data is missing ---
        name = po.get('name', '')
        if not name or price <= 0:
            continue

        # --- Extract all attributes ---
        device_id = po.get('id', '')
        description = po.get('description', '')
        characteristics = po.get('characteristic', []) # Correct key is 'characteristic'
        
        brand = get_char_value(characteristics, 'manufacturerContact')
        if brand:
            brand = brand.split(' ')[0]

        features = get_char_value(characteristics, 'features')
        storage = get_char_value(characteristics, 'storage')

        image = ''
        attachments = po.get('attachments', [])
        for attachment in attachments:
            if attachment.get('group') == 'thumbnail':
                image = attachment.get('url', '')
                break
        
        color = ''
        name_parts = name.split(',')
        if len(name_parts) > 1:
            color_part = name_parts[-1].strip()
            # Avoid picking up storage specs as color
            if 'gb' not in color_part.lower() and 'tb' not in color_part.lower():
                 color = color_part

        rating = round(random.uniform(4.0, 5.0), 1)

        devices.append({
            'id': device_id,
            'name': name,
            'brand': brand,
            'price': price,
            'original_price': price,
            'image': image,
            'description': description,
            'features': features,
            'storage': storage,
            'color': color,
            'rating': rating
        })
    return devices

def write_to_csv(devices, csv_file):
    if not devices:
        print("No devices to write.")
        return

    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=devices[0].keys())
        writer.writeheader()
        writer.writerows(devices)

if __name__ == '__main__':
    devices_to_add = extract_device_data('listing.json', num_devices=10)
    if devices_to_add:
        write_to_csv(devices_to_add, 'sample_devices.csv')
        print(f"Wrote {len(devices_to_add)} devices to sample_devices.csv")
