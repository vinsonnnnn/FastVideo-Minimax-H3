"""Build a private server-owned catalog from validated benchmark plans.

Input contains installed plugin templates (possibly sealed payloads). Output
belongs outside the web root and must never be served as a static file.
"""
import argparse
import json
from pathlib import Path

VIDEO_DURATION = {
    'API-U03-minimax_h3_light2v-文生视频加速版API-V2': '141:value',
    'API-U03-minimax_h3_文生视频基础版API-V2': '139:value',
    'API-U00-闹闹版_s': '259:seconds',
    'API-U06V9-9图3音': '3892:seconds',
    'API-U22-9图3音': '403:seconds',
    'API-U30': '259:seconds',
}


def build(plans):
    result = []
    for item in plans:
        if item['id'] not in VIDEO_DURATION and item['category'] != '图像':
            continue
        template = item['workflow_template']
        config = template['_api_config']
        inputs = dict(item['input_values'])
        required = item['id'] in VIDEO_DURATION and not item['id'].startswith('API-U03')
        for key, enabled in config['enabledParams'].items():
            if not enabled:
                continue
            node, field = key.split(':', 1)
            alias = config.get('apiNames', {}).get(key, field)
            if field.startswith('ref_') or field in ('image', 'video', 'audio', 'image_path', 'video_path'):
                inputs[alias] = None
                template[node]['inputs'][field] = None
                config['formValues'][key] = None
                required |= not field.startswith('ref_')
            if field in ('prompt', 'text', 'positive'):
                inputs[alias] = ''
                template[node]['inputs'][field] = ''
                config['formValues'][key] = ''
        # Single-image workflows may retain a LoadImage node that is not an API
        # input. Record these server-owned slots so no fixture leaks into jobs.
        image_slots = []
        for node_id, node in template.items():
            if not isinstance(node, dict):
                continue
            if node.get('class_type') == 'LoadImage':
                image_slots.append(f'{node_id}:image')
        required |= bool(image_slots)
        result.append({'id': item['id'], 'submit_workflow_id': item['submit_workflow_id'],
                       'category': item['category'], 'input_values': inputs,
                       'workflow_template': template, 'duration_key': VIDEO_DURATION.get(item['id']),
                       'reference_required': required, 'image_slots': image_slots})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plans', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = build(json.loads(args.plans.read_text()))
    args.output.write_text(json.dumps(result, ensure_ascii=False))
    args.output.chmod(0o600)
    print(f'Created private catalog: {len(result)} workflows')
