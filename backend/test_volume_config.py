#!/usr/bin/env python3
"""
Test script to verify VolumeConfig generation
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.config_generator import ConfigGenerator
from app.db.database import SessionLocal
from app.crud import volume as volume_crud
from app.schemas.volume import VolumeConfigCreate

def test_volume_config_generation():
    """Test VolumeConfig generation"""
    print("=" * 70)
    print("Testing VolumeConfig Generation")
    print("=" * 70)

    # Create a database session
    db = SessionLocal()

    try:
        # Check if EPHEMERAL config exists
        ephemeral_config = volume_crud.get_volume_config_by_name(db, "EPHEMERAL")

        if not ephemeral_config:
            print("\n[INFO] No EPHEMERAL volume config found in database.")
            print("[INFO] Creating a test EPHEMERAL config...")

            # Create a test config
            test_config = VolumeConfigCreate(
                name="EPHEMERAL",
                max_size="100GB",
                min_size="2GB",
                disk_selector_match=None,
                grow=False
            )
            ephemeral_config = volume_crud.create_volume_config(db, test_config)
            print(f"[SUCCESS] Created test EPHEMERAL config: max_size={ephemeral_config.max_size}, min_size={ephemeral_config.min_size}")
        else:
            print(f"\n[INFO] Found existing EPHEMERAL config:")
            print(f"  - max_size: {ephemeral_config.max_size}")
            print(f"  - min_size: {ephemeral_config.min_size}")
            print(f"  - disk_selector_match: {ephemeral_config.disk_selector_match}")
            print(f"  - grow: {ephemeral_config.grow}")

        # Test the volume config generation
        print("\n" + "=" * 70)
        print("Testing _generate_volume_configs method")
        print("=" * 70)

        generator = ConfigGenerator()
        volume_configs = generator._generate_volume_configs(db)

        if volume_configs:
            print(f"\n[SUCCESS] Generated {len(volume_configs)} VolumeConfig document(s):")
            for i, vol_config in enumerate(volume_configs, 1):
                print(f"\nVolumeConfig Document #{i}:")
                print(f"  apiVersion: {vol_config.get('apiVersion')}")
                print(f"  kind: {vol_config.get('kind')}")
                print(f"  name: {vol_config.get('name')}")
                if 'provisioning' in vol_config:
                    print(f"  provisioning:")
                    prov = vol_config['provisioning']
                    if 'diskSelector' in prov:
                        print(f"    diskSelector:")
                        print(f"      match: {prov['diskSelector'].get('match')}")
                    if 'minSize' in prov:
                        print(f"    minSize: {prov['minSize']}")
                    if 'maxSize' in prov:
                        print(f"    maxSize: {prov['maxSize']}")
                    if 'grow' in prov:
                        print(f"    grow: {prov['grow']}")
        else:
            print("\n[INFO] No VolumeConfig documents generated (no volumes configured)")

        # Test the full config generation with a sample MAC
        print("\n" + "=" * 70)
        print("Testing full config generation with VolumeConfig")
        print("=" * 70)

        test_mac = "00:11:22:33:44:55"
        print(f"\n[INFO] Generating config for test MAC: {test_mac}")

        config_yaml, output_path = generator.generate_config_from_params(
            mac_address=test_mac,
            node_type="worker",
            hostname="test-worker-01",
            ip_address="10.0.128.10/24",
            save_to_disk=False  # Don't save to disk for testing
        )

        # Count YAML documents
        doc_count = config_yaml.count('---') + 1
        print(f"\n[SUCCESS] Generated configuration with {doc_count} YAML document(s)")

        # Check if VolumeConfig is present
        if 'kind: VolumeConfig' in config_yaml:
            print("[SUCCESS] VolumeConfig document found in generated YAML!")

            # Extract and display the VolumeConfig section
            print("\n" + "-" * 70)
            print("VolumeConfig Section:")
            print("-" * 70)

            # Find the VolumeConfig section
            lines = config_yaml.split('\n')
            in_volume_config = False
            volume_config_lines = []

            for line in lines:
                if 'kind: VolumeConfig' in line:
                    in_volume_config = True
                    # Include a few lines before for context
                    if len(volume_config_lines) >= 2:
                        volume_config_lines = volume_config_lines[-2:]

                if in_volume_config:
                    volume_config_lines.append(line)
                    # Stop at next document or end
                    if line.strip() == '---' and len(volume_config_lines) > 5:
                        break
                else:
                    volume_config_lines.append(line)

            print('\n'.join(volume_config_lines[:30]))  # Show first 30 lines of VolumeConfig
        else:
            print("[WARNING] VolumeConfig document NOT found in generated YAML")

        print("\n" + "=" * 70)
        print("Test completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

    return True

if __name__ == "__main__":
    success = test_volume_config_generation()
    sys.exit(0 if success else 1)
