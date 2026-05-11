"""Build a self-contained CVPR 2026 paper explorer.

Input:
  data/cvpr2026_papers.json

Output:
  output/cvpr2026_explorer.html
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "cvpr2026_papers.json"
OUT = ROOT / "output" / "cvpr2026_explorer.html"
METHOD_OUT = ROOT / "output" / "cvpr2026_semantic_methodology.html"
AFF_RANKINGS_OUT = ROOT / "output" / "cvpr2026_affiliation_rankings.md"
AFF_RANKINGS_HTML_OUT = ROOT / "output" / "cvpr2026_affiliation_rankings.html"
OTHER_AFFILIATIONS_OUT = ROOT / "output" / "cvpr2026_other_affiliations.md"
OTHER_AFFILIATIONS_HTML_OUT = ROOT / "output" / "cvpr2026_other_affiliations.html"
AFF_REGION_TABLE_PATH = ROOT / "classification" / "aff_region_table.json"
MANUAL_AFF_REGION_LOOKUP_PATH = ROOT / "classification" / "manual_other_aff_region_lookup.json"
SEMANTIC_TOPICS_PATH = ROOT / "classification" / "semantic_topics.json"
ARXIV_LINKS_PATH = ROOT / "classification" / "arxiv_links.json"
AFF_REGION_TABLE = json.loads(AFF_REGION_TABLE_PATH.read_text(encoding="utf-8")) if AFF_REGION_TABLE_PATH.exists() else {}
MANUAL_AFF_REGION_LOOKUP_ROWS = json.loads(MANUAL_AFF_REGION_LOOKUP_PATH.read_text(encoding="utf-8")) if MANUAL_AFF_REGION_LOOKUP_PATH.exists() else []

OFFICIAL_STATS = {
    "submissions": 16092,
    "accepted": 4090,
    "acceptance_rate": "25.42%",
    "findings": 1717,
    "dates": "June 3-7, 2026",
    "location": "Denver, Colorado",
    "decision_date": "February 20, 2026",
}

NOISE_REGION = "Unknown / Independent / Noise"

COUNTRY_HINTS: list[tuple[str, list[str]]] = [
    ("USA", ["united states", "usa", "u.s.", "mit", "stanford", "harvard", "berkeley", "cmu", "carnegie mellon", "princeton", "cornell", "columbia university", "university of washington", "university of california", "google", "meta", "microsoft", "nvidia", "apple", "adobe", "amazon", "openai", "caltech", "ucsd", "ucla", "uiuc", "gatech", "georgia tech"]),
    ("China", ["china", "chinese academy", "tsinghua", "peking university", "beihang", "zhejiang university", "shanghai jiao", "fudan", "nanjing university", "huawei", "tencent", "alibaba", "bytedance", "sensetime", "hong kong", "hkust", "cuhk", "city university of hong kong", "macau"]),
    ("South Korea", ["korea", "kaist", "snu", "seoul national", "postech", "yonsei", "korea university", "dgist", "gist", "unist", "lg ai", "naver"]),
    ("Japan", ["japan", "tokyo", "kyoto", "osaka", "tohoku", "riken", "sony", "nec", "preferred networks"]),
    ("Germany", ["germany", "munich", "tubingen", "tuebingen", "max planck", "rwth", "tum", "fraunhofer", "heidelberg"]),
    ("United Kingdom", ["united kingdom", "uk", "u.k.", "oxford", "cambridge", "imperial college", "ucl", "edinburgh", "surrey"]),
    ("France", ["france", "inria", "sorbonne", "paris", "grenoble", "centrale", "cnrs"]),
    ("Canada", ["canada", "toronto", "waterloo", "mcgill", "ubc", "alberta", "montreal", "mila"]),
    ("Singapore", ["singapore", "nus", "ntu singapore", "a*star", "s-lab"]),
    ("Australia", ["australia", "monash", "anu", "unsw", "sydney", "melbourne", "adelaide"]),
    ("Switzerland", ["switzerland", "eth", "epfl", "zurich", "lausanne"]),
    ("Italy", ["italy", "politecnico", "sapienza", "bologna", "trento", "padova"]),
    ("Netherlands", ["netherlands", "delft", "amsterdam", "eindhoven", "utrecht"]),
    ("India", ["india", "iit ", "iisc", "iiit", "indian institute", "ashoka"]),
    ("Israel", ["israel", "technion", "hebrew university", "tel aviv", "weizmann"]),
    ("Spain", ["spain", "barcelona", "madrid", "valencia", "upc"]),
    ("Sweden", ["sweden", "kth", "lund", "chalmers", "uppsala"]),
    ("Taiwan", ["taiwan", "national taiwan", "academia sinica", "nthu", "nycu"]),
    ("Bulgaria", ["bulgaria", "insait", "sofia university", "sofia un."]),
]


AFF_REGION_OVERRIDES: dict[str, str] = {
    "Allen Institute for AI": "USA",
    "Allen Institute for Artificial Intelligence": "USA",
    "Bauhaus-Universität Weimar": "Germany",
    "Bauhaus-University Weimar": "Germany",
    "Bayerische Julius-Maximilians-Universität Würzburg": "Germany",
    "Bergische Universität Wuppertal": "Germany",
    "Brunel University of London": "United Kingdom",
    "ByteDance": "China",
    "Canva Pty Ltd.": "Australia",
    "CUHK": "China",
    "City University of Hong Kong": "China",
    "Daegu Gyeongbuk Institute of Science & Technology": "South Korea",
    "Daegu Gyeongbuk Institute of Science and Technology": "South Korea",
    "DGIST": "South Korea",
    "DENSO Corporation": "Japan",
    "DENSO CORPORATION": "Japan",
    "Denso IT Laboratory, Inc.": "Japan",
    "Duksung Women's University": "South Korea",
    "Eberhard-Karls-Universität Tübingen": "Germany",
    "EPFL": "Switzerland",
    "ETRI": "South Korea",
    "FAIR": "USA",
    "Ethz": "Switzerland",
    "ETHZ - ETH Zurich": "Switzerland",
    "Freie Universität Berlin": "Germany",
    "Forschungszentrum Juelich GmbH": "Germany",
    "Forschungszentrum Jülich GmbH": "Germany",
    "Georg-August Universität Göttingen": "Germany",
    "Georgia Tech": "USA",
    "Google PAIR": "USA",
    "Google / DeepMind": "USA",
    "Hanbat National University": "South Korea",
    "Hansung University Seoul": "South Korea",
    "HFUT": "China",
    "HKU": "China",
    "HKUST": "China",
    "Ho Chi Minh City University of Technology": "Vietnam",
    "Humboldt Universität Berlin": "Germany",
    "Humboldt-Universität zu Berlin": "Germany",
    "Hunyuan": "China",
    "IEEE International Conferenc 2026": NOISE_REGION,
    "INHA UNIVERSITY": "South Korea",
    "KAIST": "South Korea",
    "Klleon AI Research": "South Korea",
    "Institute of Artificial Intelligence and Robotics, Xi’an Jiaotong University": "China",
    "Institute of Science Tokyo / Denso IT Laboratory, Inc.": "Japan",
    "Johann Wolfgang Goethe Universität Frankfurt am Main": "Germany",
    "Honda Research Institute US": "USA",
    "Honda Research Institute USA": "USA",
    "IISER Bhopal": "India",
    "KENTECH": "South Korea",
    "Kyoto Institute of Technology": "Japan",
    "Kyushu University, Faculty of Information Science and Electrical Engineering": "Japan",
    "King Abdul Aziz University": "Saudi Arabia",
    "Korean Institute of Energy Technology": "South Korea",
    "Leibniz University of Hannover": "Germany",
    "LinkedIn Corporation": "USA",
    "Linkedin": "USA",
    "London School of Economics": "United Kingdom",
    "London School of Economics and Political Science": "United Kingdom",
    "Ludwig-Maximilians-Universität München": "Germany",
    "Max-Planck Institute for Informatics": "Germany",
    "MIRALab, University of Geneva": "Switzerland",
    "Mitsubishi Electric Corporation": "Japan",
    "Monash University, Malaysia Campus": "Malaysia",
    "Monash University": "Australia",
    "MSR": "USA",
    "Meta": "USA",
    "National Institute of Informatics": "Japan",
    "NTU Singapore": "Singapore",
    "NUS": "Singapore",
    "National Tsing Hua University": "Taiwan",
    "National Tsinghua University": "Taiwan",
    "NII": "Japan",
    "NJUST": "China",
    "NUIST": "China",
    "None": NOISE_REGION,
    "Northwest University": "China",
    "Northwest University Xi'an": "China",
    "New York University FAIR, Meta": "USA",
    "NAVER AI Lab": "South Korea",
    "Peking University": "China",
    "POSTECH": "South Korea",
    "Independent": NOISE_REGION,
    "Individual Researcher": NOISE_REGION,
    "Queen's University Belfast": "United Kingdom",
    "Rheinische Friedrich-Wilhelms Universität Bonn": "Germany",
    "Rheinland-Pfälzische Technische Universität": "Germany",
    "Royal Melbourne Institute of Technology": "Australia",
    "Samsung AI Center - Cambridge": "United Kingdom",
    "Samsung AI Center Cambridge": "United Kingdom",
    "Samsung AI Center - Toronto": "Canada",
    "Samsung AI Centre Toronto": "Canada",
    "Samsung Electronics (AI Center–Toronto)": "Canada",
    "AI Center - Toronto, Samsung Electronics": "Canada",
    "Ruhr-Universität Bochum": "Germany",
    "Ruhr-Universtät Bochum": "Germany",
    "Samsung R&D Institute, Bangalore": "India",
    "Samsung research institute banglore": "India",
    "Samsung Research Bangalore": "India",
    "Samsung R&D Institute India-Bangalore Private Limited": "India",
    "Sejong University": "South Korea",
    "Shanghai AI Laboratory": "China",
    "Shanghai Jiao Tong University": "China",
    "SIAT": "China",
    "School of Information Science and Technology, Northwest University": "China",
    "School of Information Science and Technology, Northwest University,": "China",
    "SRIB Bangalore": "India",
    "STUDENT": NOISE_REGION,
    "student": NOISE_REGION,
    "Technische Universität Carolo-Wilhelmina Braunschweig": "Germany",
    "Technische Universität Dresden": "Germany",
    "Technische Universität Graz": "Austria",
    "Technische Universität München - ImFusion": "Germany",
    "Tencent": "China",
    "Tencent Lightspeed Studios Singapore": "Singapore",
    "The Allen Institute for Artificial Intelligence": "USA",
    "The University of British Columbia": "Canada",
    "The University of British Columbia, Vector Institute": "Canada",
    "Tsinghua University": "China",
    "Trinity College Dublin": "Ireland",
    "Toyota Motor Europe": "Belgium",
    "Toyota Motors Europe": "Belgium",
    "USTB": "China",
    "USTC": "China",
    "UniZg-FER": "Croatia",
    "Universität Augsburg": "Germany",
    "Universität für Bodenkultur Wien": "Austria",
    "Universität Innsbruck": "Austria",
    "Universität Kaiserslautern": "Germany",
    "Universität Kassel": "Germany",
    "Universität Köln": "Germany",
    "Universität Konstanz": "Germany",
    "Universität Osnabrück": "Germany",
    "Universität Potsdam": "Germany",
    "Universität Siegen": "Germany",
    "Universität St. Gallen": "Switzerland",
    "Universität Stuttgart": "Germany",
    "Universität Zürich": "Switzerland",
    "University of Dublin, Trinity College": "Ireland",
    "University of Dundee": "United Kingdom",
    "University of East Anglia": "United Kingdom",
    "University of Geneva": "Switzerland",
    "University of Cambridge": "United Kingdom",
    "University Bonn": "Germany",
    "University Goettingen": "Germany",
    "University of Jyväskylä": "Finland",
    "University of Limerick": "Ireland",
    "University of Lübeck": "Germany",
    "University of Milano-Bicocca": "Italy",
    "UNIST": "South Korea",
    "University of Oregon": "USA",
    "University of New South Wales (UNSW Sydney)": "Australia",
    "University of Nottingham, Malaysia Campus": "Malaysia",
    "University of Ljubljana": "Slovenia",
    "University of Science, VNU-HCM": "Vietnam",
    "University of St. Gallen": "Switzerland",
    "University of St.Gallen": "Switzerland",
    "University of Teesside": "United Kingdom",
    "University Tübingen": "Germany",
    "University of Tuebingen": "Germany",
    "University of Trento": "Italy",
    "University of Turin": "Italy",
    "Università degli Studi di Verona": "Italy",
    "Université de Lille": "France",
    "Université de Lorraine": "France",
    "Université de Strasbourg": "France",
    "Ulsan National Institute of Science & Technology": "South Korea",
    "UZH": "Switzerland",
    "Vietnam National University Hanoi": "Vietnam",
    "Vietnam National University, Hanoi": "Vietnam",
    "VNU University of Engineering and Technology": "Vietnam",
    "Vector Institute": "Canada",
    "VinUniversity": "Vietnam",
    "bitdeer": NOISE_REGION,
    "나": NOISE_REGION,
}


AFF_REGION_OVERRIDES.update({
    "ANU": "Australia",
    "CASIA": "China",
    "Carnegie Mellon University": "USA",
    "Chinese Academy of Sciences": "China",
    "EPFL": "Switzerland",
    "ETH Zurich": "Switzerland",
    "Fudan University": "China",
    "Harvard University": "USA",
    "Northwestern Polytechnical University": "China",
    "GIST": "South Korea",
    "Institute of Computing Technology, CAS": "China",
    "KIT": "Germany",
    "MIT": "USA",
    "NII": "Japan",
    "Nanjing University": "China",
    "Samsung": "South Korea",
    "Samsung AI Center Cambridge": "United Kingdom",
    "Samsung AI Center Toronto": "Canada",
    "Samsung Research Bangalore": "India",
    "Sun Yat-sen University": "China",
    "TUM": "Germany",
    "UC Berkeley": "USA",
    "UCLA": "USA",
    "UCSD": "USA",
    "Zhejiang University": "China",
})


TAXONOMY: list[dict[str, str | list[str]]] = [
    {"phylum": "Multimodal & Language", "class": "Vision-Language Models", "order": "MLLM Reasoning", "genus": "VLM / MLLM", "patterns": ["vision-language", "vision language", "vlm", "mllm", "multimodal large language", "visual language"]},
    {"phylum": "Multimodal & Language", "class": "Language Grounding", "order": "Grounded Understanding", "genus": "Grounding", "patterns": ["grounding", "grounded", "referring", "phrase localization", "visual question answering", "vqa"]},
    {"phylum": "Multimodal & Language", "class": "Agents", "order": "GUI / Web Agents", "genus": "Agentic AI", "patterns": ["agent", "gui", "web agent", "tool", "reasoning", "chain-of-thought", "cot"]},
    {"phylum": "Generative Models", "class": "Diffusion Models", "order": "Image Generation", "genus": "Diffusion", "patterns": ["diffusion", "score-based", "denoising", "rectified flow", "flow matching"]},
    {"phylum": "Generative Models", "class": "Video Generation", "order": "Temporal Synthesis", "genus": "Video Generation", "patterns": ["video generation", "text-to-video", "image-to-video", "motion generation", "video diffusion"]},
    {"phylum": "Generative Models", "class": "Editing & Personalization", "order": "Controllable Generation", "genus": "Image Editing", "patterns": ["editing", "edit", "personalized", "customized", "controlnet", "stylization", "style transfer"]},
    {"phylum": "3D Vision & Geometry", "class": "Neural Rendering", "order": "Gaussian / NeRF", "genus": "3D Gaussian Splatting", "patterns": ["gaussian splatting", "3dgs", "4dgs", "splatting", "nerf", "neural radiance"]},
    {"phylum": "3D Vision & Geometry", "class": "Reconstruction", "order": "Surface / Scene Reconstruction", "genus": "3D Reconstruction", "patterns": ["reconstruction", "surface", "mesh", "signed distance", "sdf", "shape completion", "multi-view stereo"]},
    {"phylum": "3D Vision & Geometry", "class": "Pose & Registration", "order": "Camera/Object Pose", "genus": "Pose Estimation", "patterns": ["pose estimation", "6d pose", "registration", "bundle adjustment", "calibration", "slam"]},
    {"phylum": "3D Vision & Geometry", "class": "Point Clouds", "order": "Point Representation", "genus": "Point Cloud", "patterns": ["point cloud", "lidar", "voxel", "occupancy", "bev"]},
    {"phylum": "Recognition & Classification", "class": "Image Classification", "order": "Representation Learning", "genus": "Classification", "patterns": ["classification", "recognition", "open-vocabulary", "zero-shot", "few-shot"]},
    {"phylum": "Recognition & Classification", "class": "Retrieval", "order": "Image/Text Retrieval", "genus": "Retrieval", "patterns": ["retrieval", "re-identification", "reid", "matching", "feature matching"]},
    {"phylum": "Detection & Tracking", "class": "Object Detection", "order": "Generic Detection", "genus": "Detection", "patterns": ["detection", "detector", "detr", "yolo", "open world object"]},
    {"phylum": "Detection & Tracking", "class": "Tracking", "order": "Object Tracking", "genus": "Tracking", "patterns": ["tracking", "track", "multi-object", "mot"]},
    {"phylum": "Segmentation & Dense Prediction", "class": "Segmentation", "order": "Semantic / Instance Segmentation", "genus": "Segmentation", "patterns": ["segmentation", "segment", "mask", "sam", "panoptic"]},
    {"phylum": "Segmentation & Dense Prediction", "class": "Depth & Flow", "order": "Dense Geometry", "genus": "Depth / Optical Flow", "patterns": ["depth", "stereo", "optical flow", "scene flow", "disparity"]},
    {"phylum": "Video & Motion", "class": "Video Understanding", "order": "Temporal Reasoning", "genus": "Video Understanding", "patterns": ["video understanding", "long video", "action recognition", "temporal", "event prediction"]},
    {"phylum": "Video & Motion", "class": "Human Motion", "order": "Pose / Motion", "genus": "Human Motion", "patterns": ["human motion", "human pose", "gesture", "avatar", "body", "humanoid"]},
    {"phylum": "Low-level Vision", "class": "Restoration", "order": "Image Restoration", "genus": "Restoration", "patterns": ["super-resolution", "deblurring", "denoising", "dehazing", "low-light", "restoration"]},
    {"phylum": "Low-level Vision", "class": "Image Quality", "order": "Quality Assessment", "genus": "IQA", "patterns": ["image quality", "quality assessment", "compression", "codec", "bitrate"]},
    {"phylum": "Learning Algorithms", "class": "Optimization", "order": "Training Methods", "genus": "Optimization", "patterns": ["optimization", "training", "gradient", "fine-tuning", "lora", "adapter"]},
    {"phylum": "Learning Algorithms", "class": "Self-supervised Learning", "order": "Pretraining", "genus": "Self-supervised", "patterns": ["self-supervised", "contrastive", "masked", "pre-training", "pretraining"]},
    {"phylum": "Learning Algorithms", "class": "Efficient ML", "order": "Compression / Pruning", "genus": "Efficient Models", "patterns": ["efficient", "pruning", "quantization", "distillation", "low-rank", "token reduction"]},
    {"phylum": "Robustness & Safety", "class": "Robustness", "order": "OOD / Domain Shift", "genus": "Robustness", "patterns": ["robust", "out-of-distribution", "ood", "domain adaptation", "domain generalization", "test-time"]},
    {"phylum": "Robustness & Safety", "class": "Security & Safety", "order": "Adversarial / Safe AI", "genus": "Safety", "patterns": ["adversarial", "attack", "backdoor", "jailbreak", "safety", "trustworthy", "hallucination"]},
    {"phylum": "Robotics & Embodied AI", "class": "Embodied Agents", "order": "Navigation / Manipulation", "genus": "Embodied AI", "patterns": ["embodied", "robot", "navigation", "manipulation", "grasp", "locomotion", "vision-language-action", "vla"]},
    {"phylum": "Autonomous Driving", "class": "Driving Perception", "order": "Perception / Planning", "genus": "Autonomous Driving", "patterns": ["autonomous driving", "driving", "vehicle", "traffic", "lane", "bev perception"]},
    {"phylum": "Medical & Scientific Imaging", "class": "Medical Vision", "order": "Clinical Imaging", "genus": "Medical Imaging", "patterns": ["medical", "clinical", "ct", "mri", "pathology", "slide", "segmentation for medical"]},
    {"phylum": "Remote Sensing & Earth", "class": "Remote Sensing", "order": "Satellite / Aerial", "genus": "Remote Sensing", "patterns": ["remote sensing", "satellite", "aerial", "hyperspectral", "earth observation"]},
    {"phylum": "Data & Evaluation", "class": "Datasets & Benchmarks", "order": "Evaluation", "genus": "Benchmark", "patterns": ["benchmark", "dataset", "evaluation", "survey", "metric"]},
    {"phylum": "Computational Imaging", "class": "Sensors & Cameras", "order": "Novel Imaging", "genus": "Computational Imaging", "patterns": ["event camera", "camera", "sensor", "radar", "spectral", "defocus", "non-line-of-sight", "imaging"]},
]


def split_semicolon(value: str) -> list[str]:
    return [x.strip() for x in str(value or "").split(";") if x.strip()]


AFFILIATION_ALIASES: list[tuple[str, str]] = [
    ("Korea Advanced Institute of Science & Technology", "KAIST"),
    ("Korea Advanced Institute of Science and Technology", "KAIST"),
    ("KAIST", "KAIST"),
    ("Daegu Gyeongbuk Institute of Science & Technology", "DGIST"),
    ("Daegu Gyeongbuk Institute of Science and Technology", "DGIST"),
    ("DGIST", "DGIST"),
    ("NAVER AI Lab", "NAVER AI Lab"),
    ("Klleon AI Research", "Klleon AI Research"),
    ("Anigma Technologies", "Anigma Technologies"),
    ("Shanghai Jiaotong University", "Shanghai Jiao Tong University"),
    ("Shanghai JiaoTong University", "Shanghai Jiao Tong University"),
    ("Shanghai Jiao Tong Univeristy", "Shanghai Jiao Tong University"),
    ("Shanghai Jiao Tong University", "Shanghai Jiao Tong University"),
    ("SJTU", "Shanghai Jiao Tong University"),
    ("上海交通大学", "Shanghai Jiao Tong University"),
    ("Shanghai Artificial Intelligence Laboratory", "Shanghai AI Laboratory"),
    ("Shanghai Aritifcal Intelligence Laboratory", "Shanghai AI Laboratory"),
    ("Shanghai AI Laboratory", "Shanghai AI Laboratory"),
    ("Shanghai AI Lab", "Shanghai AI Laboratory"),
    ("Shanghai AI LAB", "Shanghai AI Laboratory"),
    ("Tsinghua University", "Tsinghua University"),
    ("Tsinghua Univeresity", "Tsinghua University"),
    ("THU", "Tsinghua University"),
    ("SIGS, Tsinghua University", "Tsinghua University"),
    ("University of Science and Technology of China", "USTC"),
    ("University Of Science And Technology Of China", "USTC"),
    ("USTC", "USTC"),
    ("中国科学技术大学", "USTC"),
    ("Peking University Shenzhen Graduate School", "Peking University"),
    ("Peking University", "Peking University"),
    ("PKU", "Peking University"),
    ("PEKING UNIVERSITY", "Peking University"),
    ("The Hong Kong University of Science and Technology", "HKUST"),
    ("Hong Kong University of Science and Technology", "HKUST"),
    ("HKUST(GZ)", "HKUST"),
    ("HKUST", "HKUST"),
    ("The Chinese University of Hong Kong, Shenzhen", "CUHK"),
    ("The Chinese University of Hong Kong", "CUHK"),
    ("Chinese University of Hong Kong", "CUHK"),
    ("MMLab of CUHK", "CUHK"),
    ("CUHK", "CUHK"),
    ("The University of Hong Kong", "HKU"),
    ("University of Hong Kong", "HKU"),
    ("University of Hongkong", "HKU"),
    ("City University of Hong Kong", "City University of Hong Kong"),
    ("CityUHK", "City University of Hong Kong"),
    ("National University of Singapore", "NUS"),
    ("NUS School of Computing", "NUS"),
    ("NUS", "NUS"),
    ("Nanyang Technological University", "NTU Singapore"),
    ("Nanyang Technology University", "NTU Singapore"),
    ("NTU Singapore", "NTU Singapore"),
    ("NTU", "NTU Singapore"),
    ("Meta Reality Labs Research", "Meta"),
    ("Reality Labs Research, Meta", "Meta"),
    ("Reality Labs, Meta", "Meta"),
    ("Meta Reality Labs", "Meta"),
    ("Meta Platforms", "Meta"),
    ("Facebook Reality Labs", "Meta"),
    ("Facebook", "Meta"),
    ("Meta AI", "Meta"),
    ("FAIR at Meta", "Meta"),
    ("FAIR", "Meta"),
    ("Meta", "Meta"),
    ("Google DeepMind", "Google / DeepMind"),
    ("Google Deepmind", "Google / DeepMind"),
    ("Google Research", "Google / DeepMind"),
    ("Google Brain", "Google / DeepMind"),
    ("DeepMind", "Google / DeepMind"),
    ("Google", "Google / DeepMind"),
    ("ByteDance Inc.", "ByteDance"),
    ("ByteDance", "ByteDance"),
    ("Bytedance", "ByteDance"),
    ("TikTok", "ByteDance"),
    ("Tiktok", "ByteDance"),
    ("PICO, ByteDance", "ByteDance"),
    ("Tencent Youtu Lab", "Tencent"),
    ("Tencent Hunyuan", "Tencent"),
    ("Tencent ARC Lab", "Tencent"),
    ("Tencent AI Lab", "Tencent"),
    ("WeChat", "Tencent"),
    ("Tencent", "Tencent"),
    ("Pohang University of Science & Technology", "POSTECH"),
    ("Pohang University of Science and Technology", "POSTECH"),
    ("POSTECH", "POSTECH"),
    ("Ulsan National Institute of Science & Technology", "UNIST"),
    ("Ulsan National Institute of Science and Technology", "UNIST"),
    ("UNIST", "UNIST"),
    ("Electronics and Telecommunications Research Institute", "ETRI"),
    ("ETRI", "ETRI"),
    ("Georgia Institute of Technology", "Georgia Tech"),
    ("Georgia Tech", "Georgia Tech"),
    ("UIUC", "UIUC"),
    ("University of Illinois Urbana-Champaign", "UIUC"),
    ("University of Illinois at Urbana-Champaign", "UIUC"),
    ("Oregon State University", "Oregon State University"),
    ("University of Oregon", "University of Oregon"),
    ("Oregon", "University of Oregon"),
    ("Google PAIR", "Google / DeepMind"),
    ("PAIR", "Google / DeepMind"),
    ("Amazon AGI", "Amazon AGI"),
    ("MSR", "Microsoft"),
    ("Carnegie Mellon University", "Carnegie Mellon University"),
    ("CMU", "Carnegie Mellon University"),
    ("ETHZ - ETH Zurich", "ETH Zurich"),
    ("ETH Zürich", "ETH Zurich"),
    ("ETH Zurich", "ETH Zurich"),
    ("ETH", "ETH Zurich"),
    ("INSAIT Sofia", "INSAIT"),
    ("INSAIT", "INSAIT"),
    ("Sofia Un. St. Kliment Ohridski", "Sofia University"),
    ("Sofia University \"St. Kliment Ohridski\"", "Sofia University"),
    ("Sofia University", "Sofia University"),
    ("Google DeepMind", "Google / DeepMind"),
    ("Google Research", "Google / DeepMind"),
    ("Google Brain", "Google / DeepMind"),
    ("Google", "Google / DeepMind"),
    ("Microsoft Research", "Microsoft"),
    ("Microsoft", "Microsoft"),
    ("TUM", "TUM"),
    ("Technical University of Munich", "TUM"),
    ("Technische Universität München", "TUM"),
    ("HKUST", "HKUST"),
    ("The Hong Kong University of Science and Technology", "HKUST"),
    ("Peking University", "Peking University"),
    ("Canva Pty Ltd.", "Canva Pty Ltd."),
    ("University of Ljubljana", "University of Ljubljana"),
    ("The University of British Columbia", "The University of British Columbia"),
    ("Vector Institute", "Vector Institute"),
    ("VinUniversity", "VinUniversity"),
    ("Monash University", "Monash University"),
    ("New York University", "New York University"),
    ("FAIR", "Meta"),
    ("Meta", "Meta"),
    ("University of Cambridge", "University of Cambridge"),
    ("University of Tuebingen", "University of Tuebingen"),
    ("University of Tübingen", "University Tübingen"),
    ("University of Trento", "University of Trento"),
    ("University of Oxford", "University of Oxford"),
    ("University of Zurich", "University of Zurich"),
    ("University of Toronto", "University of Toronto"),
    ("Cornell", "Cornell University"),
    ("Cornell University", "Cornell University"),
    ("Inria", "Inria"),
    ("MIT", "MIT"),
    ("IIT-Hyderabad", "IIT Hyderabad"),
    ("UC Berkeley", "University of California, Berkeley"),
    ("University of California, Berkeley", "University of California, Berkeley"),
    ("NVIDIA", "NVIDIA"),
    ("MBZUAI", "Mohamed bin Zayed University of Artificial Intelligence"),
    ("Mohamed bin Zayed University of Artificial Intelligence", "Mohamed bin Zayed University of Artificial Intelligence"),
    ("DisneyResearch|Studios", "Disney Research Studios"),
    ("Disney Research Studios", "Disney Research Studios"),
    ("IBM Research", "IBM Research"),
    ("Helmholtz Munich", "Helmholtz Munich"),
]


AFFILIATION_ALIASES.extend([
    ("nanjing university", "Nanjing University"),
    ("Nanjing University", "Nanjing University"),
    ("NJU", "Nanjing University"),
    ("SUN YAT-SEN UNIVERSITY", "Sun Yat-sen University"),
    ("Sun Yat-sen University", "Sun Yat-sen University"),
    ("Sun Yat-Sen University", "Sun Yat-sen University"),
    ("SYSU", "Sun Yat-sen University"),
    ("Massachusetts Institute of Technology", "MIT"),
    ("MIT", "MIT"),
    ("Carnegie Mellon", "Carnegie Mellon University"),
    ("Carnegie Mellon University", "Carnegie Mellon University"),
    ("CMU", "Carnegie Mellon University"),
    ("University of California, San Diego", "UCSD"),
    ("UC San Diego", "UCSD"),
    ("UCSD", "UCSD"),
    ("University of California, Los Angeles", "UCLA"),
    ("UCLA", "UCLA"),
    ("University of California, Berkeley", "UC Berkeley"),
    ("UC Berkeley", "UC Berkeley"),
    ("ETHZ - ETH Zurich", "ETH Zurich"),
    ("ETH Zurich", "ETH Zurich"),
    ("ETH Zürich", "ETH Zurich"),
    ("ETHZ", "ETH Zurich"),
    ("EPFL", "EPFL"),
    ("Swiss Federal Institute of Technology Lausanne", "EPFL"),
    ("Technical University of Munich", "TUM"),
    ("Technical University Munich", "TUM"),
    ("Technische Universität München", "TUM"),
    ("TU Munich", "TUM"),
    ("TUM", "TUM"),
    ("Karlsruhe Institute of Technology", "KIT"),
    ("KIT", "KIT"),
    ("Australian National University", "ANU"),
    ("ANU", "ANU"),
    ("National Institute of Informatics", "NII"),
    ("NII", "NII"),
    ("Gwangju Institute of Science and Technology", "GIST"),
    ("GIST", "GIST"),
    ("Zhejiang University", "Zhejiang University"),
    ("zhejiang university", "Zhejiang University"),
    ("Fudan University", "Fudan University"),
    ("fudan university", "Fudan University"),
    ("Institute of Automation, CAS", "CASIA"),
    ("CASIA", "CASIA"),
    ("Institute of Computing Technology, CAS", "Institute of Computing Technology, CAS"),
    ("Chinese Academy of Sciences", "Chinese Academy of Sciences"),
    ("Samsung Research Bangalore", "Samsung Research Bangalore"),
    ("Samsung R&D Institute, Bangalore", "Samsung Research Bangalore"),
    ("SRIB Bangalore", "Samsung Research Bangalore"),
    ("Samsung AI Center - Cambridge", "Samsung AI Center Cambridge"),
    ("Samsung AI Center Cambridge", "Samsung AI Center Cambridge"),
    ("Samsung AI Center - Toronto", "Samsung AI Center Toronto"),
    ("Samsung AI Centre Toronto", "Samsung AI Center Toronto"),
    ("Samsung Electronics", "Samsung"),
    ("Samsung Research", "Samsung"),
    ("Samsung", "Samsung"),
])


def split_institutions(value: str) -> list[str]:
    institutions: list[str] = []
    for part in split_semicolon(value):
        comma_parts = [x.strip() for x in part.split(",") if x.strip()]
        if len(comma_parts) > 1 and len({plain_text(x) for x in comma_parts}) == 1:
            institutions.append(comma_parts[0])
            continue
        if not re.search(r"\s(?:/|&|and|\|)\s|,\s", part, flags=re.I):
            institutions.append(part)
            continue
        plain = plain_text(part)
        hits: list[tuple[int, int, str]] = []
        for alias, canonical in AFFILIATION_ALIASES:
            alias_plain = plain_text(alias)
            for match in re.finditer(rf"(?<![a-z0-9]){re.escape(alias_plain)}(?![a-z0-9])", plain):
                hits.append((match.start(), match.end(), canonical))
        hits.sort(key=lambda x: (-(x[1] - x[0]), x[0], x[2]))
        ranges: list[tuple[int, int]] = []
        matches: list[str] = []
        for start, end, canonical in hits:
            if any(start >= kept_start and end <= kept_end for kept_start, kept_end in ranges):
                continue
            ranges.append((start, end))
            if canonical not in matches:
                matches.append(canonical)
        if len(matches) >= 2:
            institutions.extend(matches)
        else:
            institutions.append(part)
    return institutions


def canonical_affiliation(aff: str) -> str:
    value = aff.strip()
    lower = normalize_affiliation_text(value)
    compact = lower.replace(" ", "")
    exact_kaist = {
        "kaist",
        "kaist ai",
        "kaist, visual media lab",
        "kaist, korea advanced institute of science & technology",
        "kaist, korea advanced institute of science and technology",
        "korea advanced institute of science & technology",
        "korea advanced institute of science and technology",
        "korea advanced institue of science and technology",
        "korea advanced institute of science & technology, kaist",
        "korea advanced institute of science and technology, kaist",
    }
    if lower in exact_kaist:
        return "KAIST"
    if re.fullmatch(r"kaist\s*\([^)]*\)", lower):
        return "KAIST"
    if re.fullmatch(r"korea advanced institute of science (?:&|and) technology\s*\(?kaist\)?(?:,\s*school of computing)?", lower):
        return "KAIST"
    exact_dgist = {
        "dgist",
        "daegu gyeongbuk institute of science & technology",
        "daegu gyeongbuk institute of science and technology",
        "daegu gyeongbuk institute of science & technology, dgist",
        "daegu gyeongbuk institute of science and technology, dgist",
    }
    if lower in exact_dgist:
        return "DGIST"
    if re.fullmatch(r"daegu gyeongbuk institute of science (?:&|and) technology\s*\(?dgist\)?", lower):
        return "DGIST"
    if "nanjing university" in lower or re.fullmatch(r"nju", lower):
        return "Nanjing University"
    if "sun yat sen university" in lower or re.fullmatch(r"sysu", lower):
        return "Sun Yat-sen University"
    if lower in {"mit", "massachusetts institute of technology"}:
        return "MIT"
    if "carnegie mellon" in lower or lower == "cmu":
        return "Carnegie Mellon University"
    if lower in {"ucsd", "uc san diego"} or "university of california san diego" in lower:
        return "UCSD"
    if lower == "ucla" or "university of california los angeles" in lower:
        return "UCLA"
    if lower in {"uc berkeley", "university of california berkeley"}:
        return "UC Berkeley"
    if lower in {"eth", "ethz", "eth zurich", "eth ai center"} or "eth zurich" in lower or compact in {"ethzurich", "ethzrich"}:
        return "ETH Zurich"
    if "epfl" in lower or "epf lausanne" in lower or "swiss federal institute of technology lausanne" in lower or "swiss federal technology institute of lausanne" in lower:
        return "EPFL"
    if lower in {"tum", "tu munich", "technical university munich", "technical university of munich"} or "technische universitat munchen" in lower or (compact.startswith("technischeuniversit") and "mnchen" in compact):
        return "TUM"
    if lower in {"kit", "karlsruhe institute of technology"}:
        return "KIT"
    if lower in {"anu", "australian national university"}:
        return "ANU"
    if lower in {"nii", "national institute of informatics"}:
        return "NII"
    if lower in {"gist", "gwangju institute of science and technology"}:
        return "GIST"
    if "zhejiang university" in lower:
        return "Zhejiang University"
    if "fudan university" in lower:
        return "Fudan University"
    if "northwestern polytechnical university" in lower or "northwest polytechnical university" in lower:
        return "Northwestern Polytechnical University"
    if "institute of automation cas" in lower or lower == "casia":
        return "CASIA"
    if "institute of computing technology cas" in lower:
        return "Institute of Computing Technology, CAS"
    if "chinese academy of sciences" in lower:
        return "Chinese Academy of Sciences"
    if "samsung" in lower and re.search(r"bangalore|bengaluru|india|srib", lower):
        return "Samsung Research Bangalore"
    if "samsung" in lower and "cambridge" in lower:
        return "Samsung AI Center Cambridge"
    if "samsung" in lower and "toronto" in lower:
        return "Samsung AI Center Toronto"
    if "samsung" in lower:
        return "Samsung"
    if lower in {"georgia institute of technology", "georgia tech"}:
        return "Georgia Tech"
    if lower in {"university of illinois urbana-champaign", "university of illinois at urbana-champaign", "department of computer science in uiuc", "uiuc"}:
        return "UIUC"
    if lower == "google pair" or lower == "pair":
        return "Google / DeepMind"
    if lower == "msr":
        return "Microsoft"
    if "shanghai jiaotong" in lower or "shanghai jiao tong" in lower or re.search(r"(?<![a-z0-9])sjtu(?![a-z0-9])", lower) or "上海交通大学" in value:
        return "Shanghai Jiao Tong University"
    if "shanghai artificial intelligence" in lower or "shanghai aritifcal intelligence" in lower or "shanghai ai lab" in lower or "shanghai ai laboratory" in lower:
        return "Shanghai AI Laboratory"
    if "hong kong university of science and technology" in lower or re.search(r"(?<![a-z0-9])hkust(?:\\(gz\\))?(?![a-z0-9])", lower):
        return "HKUST"
    if "chinese university of hong kong" in lower or "mmlab of cuhk" in lower or "cuhksz" in lower or re.search(r"(?<![a-z0-9])cuhk(?![a-z0-9])", lower):
        return "CUHK"
    if "city university of hong kong" in lower or "cityuhk" in lower:
        return "City University of Hong Kong"
    if "university of hongkong" in lower or "university of hong kong" in lower or re.search(r"(?<![a-z0-9])hku(?![a-z0-9])", lower):
        return "HKU"
    if "national university of singaore" in lower or "national university of singapore" in lower or re.search(r"(?<![a-z0-9])nus(?![a-z0-9])", lower):
        return "NUS"
    if "nanyang technological university" in lower or "nanyang technology university" in lower or re.search(r"(?<![a-z0-9])ntu singapore(?![a-z0-9])", lower) or re.search(r"(?<![a-z0-9])ntu(?![a-z0-9])", lower):
        return "NTU Singapore"
    if "national tsinghua university" in lower or "national tsing hua university" in lower:
        return "National Tsinghua University"
    if "tsinghua" in lower or lower == "thu":
        return "Tsinghua University"
    if "university of science and technology of china" in lower or "中国科学技术大学" in value or re.search(r"(?<![a-z0-9])ustc(?![a-z0-9])", lower):
        return "USTC"
    if "peking university" in lower or "peking. university" in lower or re.search(r"(?<![a-z0-9])pku(?![a-z0-9])", lower):
        return "Peking University"
    if "facebook" in lower or "reality labs" in lower or "meta" in lower or re.search(r"(?<![a-z0-9])fair(?![a-z0-9])", lower):
        return "Meta"
    if "google" in lower or "deepmind" in lower:
        return "Google / DeepMind"
    if "bytedance" in lower or "byte dance" in lower or "tiktok" in lower or "pico, bytedance" in lower:
        return "ByteDance"
    if "tencent lightspeed" in lower and "singapore" in lower:
        return "Tencent Lightspeed Studios Singapore"
    if "tencent" in lower or "wechat" in lower:
        return "Tencent"
    if "pohang university of science" in lower or "postech" in lower:
        return "POSTECH"
    if "ulsan national institute of science" in lower or re.search(r"(?<![a-z0-9])unist(?![a-z0-9])", lower):
        return "UNIST"
    if "electronics and telecommunications research institute" in lower or re.search(r"(?<![a-z0-9])etri(?![a-z0-9])", lower):
        return "ETRI"
    return clean_affiliation_display(value)


def unique_ordered(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        key = plain_text(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def clean_affiliation_display(value: str) -> str:
    replacements = [
        (r"\bUniveristy\b", "University"),
        (r"\bUnviersity\b", "University"),
        (r"\bUnivercity\b", "University"),
        (r"\bTechonolgy\b", "Technology"),
        (r"\bTechonology\b", "Technology"),
        (r"\bInstitue\b", "Institute"),
        (r"\bSceince\b", "Science"),
        (r"\bAritifcal\b", "Artificial"),
    ]
    text = value.strip()
    for wrong, right in replacements:
        text = re.sub(wrong, right, text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()


def plain_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def normalize_affiliation_text(value: str) -> str:
    text = plain_text(value)
    replacements = {
        "univeristy": "university",
        "unviersity": "university",
        "univercity": "university",
        "techonolgy": "technology",
        "techonology": "technology",
        "institue": "institute",
        "sceince": "science",
        "aritifcal": "artificial",
    }
    for wrong, right in replacements.items():
        text = text.replace(wrong, right)
    text = re.sub(r"[^a-z0-9&]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_region_label(region: str) -> str:
    region = str(region or "").strip()
    if region in {"Other / Needs Review", "Needs Review"}:
        return "Other"
    if region == "Unknown / Independent / Noise":
        return NOISE_REGION
    if region == "Korea":
        return "South Korea"
    if region == "UK":
        return "United Kingdom"
    if region == "Multiple":
        return "Cross-region"
    return region


MANUAL_AFF_REGION_LOOKUP: dict[str, str] = {}
MANUAL_AFF_REGION_LOOKUP_PLAIN: dict[str, str] = {}
for row in MANUAL_AFF_REGION_LOOKUP_ROWS:
    aff = str(row.get("affiliation", "")).strip()
    region = normalize_region_label(str(row.get("region", "")))
    if not aff or not region:
        continue
    MANUAL_AFF_REGION_LOOKUP[aff] = region
    MANUAL_AFF_REGION_LOOKUP_PLAIN[plain_text(aff)] = region


def corrected_region_for(lower: str) -> str | None:
    if lower in {"none", "independent", "individual researcher", "student", "na"}:
        return NOISE_REGION
    if lower in {"나"} or "ieee international conferenc" in lower:
        return NOISE_REGION
    if "bitdeer" in lower:
        return NOISE_REGION
    if lower == "hunyuan" or "tencent hunyuan" in lower:
        return "China"

    if "samsung" in lower and any(x in lower for x in ["bangalore", "bengaluru", "banglore", "india"]):
        return "India"
    if "samsung" in lower and "cambridge" in lower:
        return "United Kingdom"
    if "samsung" in lower and "toronto" in lower:
        return "Canada"
    if re.search(r"(?<![a-z0-9])srib(?![a-z0-9])", lower) and any(x in lower for x in ["bangalore", "bengaluru", "banglore"]):
        return "India"
    if "iiser bhopal" in lower:
        return "India"

    if "national tsinghua university" in lower or "national tsing hua university" in lower:
        return "Taiwan"

    swiss_tokens = [
        "zurich", "zuerich", "university of geneva", "miralab", "st.gallen", "st. gallen", "st gallen",
        "eth zurich", "lausanne",
    ]
    swiss_acronym = re.search(r"(?<![a-z0-9])(uzh|ethz|epfl)(?![a-z0-9])", lower) is not None
    if swiss_acronym or any(x in lower for x in swiss_tokens):
        return "Switzerland"

    austrian_tokens = ["innsbruck", "graz", "wien", "vienna", "bodenkultur", "klagenfurt", "linz"]
    if any(x in lower for x in austrian_tokens) and ("universitat" in lower or "technische universitat" in lower):
        return "Austria"

    german_university_tokens = [
        "tubingen", "tuebingen", "stuttgart", "munchen", "muenchen", "frankfurt", "kaiserslautern",
        "bonn", "berlin", "potsdam", "konstanz", "kassel", "koln", "koeln", "dresden", "siegen",
        "bochum", "augsburg", "weimar", "osnabruck", "freiburg", "dortmund", "hannover", "hamburg",
        "jena", "ulm", "mainz", "bremen", "leipzig", "erlangen", "wuppertal", "gottingen", "goettingen",
        "rheinland", "pfalzische", "pfaelzische", "braunschweig", "wurzburg", "wuerzburg", "lubeck", "luebeck",
        "goettingen", "gottingen",
    ]
    if "tu braunschweig" in lower:
        return "Germany"
    if ("max-planck institute for informatics" in lower or "forschungszentrum julich" in lower or
        "forschungszentrum juelich" in lower or "leibniz university of hannover" in lower or
        "university bonn" in lower or "university tubingen" in lower or "university of goettingen" in lower or
        "university goettingen" in lower or "university of lubeck" in lower or "university of augsburg" in lower or
        "bauhaus-university weimar" in lower):
        return "Germany"
    if ("universitat" in lower or "universtat" in lower) and any(x in lower for x in german_university_tokens):
        return "Germany"

    korean_tokens = [
        "daegu gyeongbuk", "inha university", "sejong university", "hanbat national", "chonnam national",
        "hansung university", "ulsan national institute", "duksung", "dankook", "dgist", "unist",
    ]
    if any(x in lower for x in korean_tokens):
        return "South Korea"

    if "queen's university belfast" in lower:
        return "United Kingdom"
    if "london school of economics" in lower or "university of east anglia" in lower or "university of dundee" in lower:
        return "United Kingdom"
    if "brunel university of london" in lower or "university of teesside" in lower or "the university of liverpool" in lower:
        return "United Kingdom"
    if "university of limerick" in lower:
        return "Ireland"
    if "university of jyvaskyla" in lower:
        return "Finland"
    if "monash university" in lower and "malaysia campus" in lower:
        return "Malaysia"
    if "university of nottingham" in lower and "malaysia campus" in lower:
        return "Malaysia"
    if "rmit" in lower and "vietnam" in lower:
        return "Vietnam"
    if re.search(r"(?<![a-z0-9])rmit(?![a-z0-9])", lower) or "royal melbourne institute of technology" in lower:
        return "Australia"
    if re.search(r"(?<![a-z0-9])unsw(?![a-z0-9])", lower) or "university of new south wales" in lower:
        return "Australia"
    if "trinity college dublin" in lower or "university of dublin, trinity" in lower:
        return "Ireland"

    japanese_tokens = [
        "national institute of informatics", "denso corporation", "denso it laboratory",
        "institute of science tokyo", "kyoto institute of technology", "mitsubishi electric corporation",
        "kyushu university",
    ]
    if re.search(r"(?<![a-z0-9])nii(?![a-z0-9])", lower) or any(x in lower for x in japanese_tokens):
        return "Japan"

    if "vnu-hcm" in lower or "vnu university" in lower or "vietnam national university" in lower or "ho chi minh city university" in lower:
        return "Vietnam"
    if "kentech" in lower or "korean institute of energy technology" in lower:
        return "South Korea"
    if "honda research institute us" in lower or "honda research institute usa" in lower:
        return "USA"
    if "toyota motor europe" in lower or "toyota motors europe" in lower:
        return "Belgium"
    if "xi'an jiaotong university" in lower or "xian jiaotong university" in lower or "xi an jiaotong university" in lower:
        return "China"
    if "northwest university" in lower:
        return "China"
    if re.search(r"(?<![a-z0-9])(ustb|hfut|njust|nuist|siat|ucas)(?![a-z0-9])", lower):
        return "China"
    if "allen institute for artificial intelligence" in lower or lower == "allen institute for ai":
        return "USA"
    if "linkedin" in lower:
        return "USA"
    if "universite de lille" in lower or "universite de strasbourg" in lower or "universite de lorraine" in lower:
        return "France"
    if "university of milano-bicocca" in lower or "universita degli studi di verona" in lower or "university of turin" in lower:
        return "Italy"
    if "king abdul aziz university" in lower:
        return "Saudi Arabia"
    if "unizg-fer" in lower:
        return "Croatia"

    return None


def country_for(aff: str) -> str:
    if aff in AFF_REGION_OVERRIDES:
        return AFF_REGION_OVERRIDES[aff]
    lower = plain_text(aff)
    if aff in MANUAL_AFF_REGION_LOOKUP:
        return MANUAL_AFF_REGION_LOOKUP[aff]
    if lower in MANUAL_AFF_REGION_LOOKUP_PLAIN:
        return MANUAL_AFF_REGION_LOOKUP_PLAIN[lower]
    corrected = corrected_region_for(lower)
    if corrected:
        return corrected
    if aff in AFF_REGION_TABLE:
        region = normalize_region_label(str(AFF_REGION_TABLE[aff]))
        if region in {"Qing dynasty", "British Empire"}:
            corrected = corrected_region_for(lower)
            return corrected or NOISE_REGION
        if region == "Cross-region":
            corrected = corrected_region_for(lower)
            return corrected or region
        return region
    for country, hints in COUNTRY_HINTS:
        if any(plain_text(h) in lower for h in hints):
            return country
    return "Other"


def match_patterns(text: str, patterns: list[str]) -> int:
    lower = plain_text(text)
    hits = 0
    for pattern in patterns:
        p = plain_text(pattern)
        if len(p) <= 4 and re.fullmatch(r"[a-z0-9]+", p):
            matched = re.search(rf"\b{re.escape(p)}\b", lower) is not None
        else:
            matched = p in lower
        if matched:
            hits += 1
    return hits


def classify(title: str, abstract: str, limit: int = 3) -> list[dict[str, str]]:
    scored = []
    seen = set()
    for node in TAXONOMY:
        patterns = node["patterns"]
        assert isinstance(patterns, list)
        title_hits = match_patterns(title, patterns)
        abstract_hits = match_patterns(abstract, patterns)
        if not title_hits and not abstract_hits:
            continue
        key = (node["phylum"], node["class"], node["order"], node["genus"])
        if key in seen:
            continue
        seen.add(key)
        # Title matches carry the taxonomy. Abstract matches are useful, but
        # less specific, so they only break ties after title hits.
        score = title_hits * 10 + min(abstract_hits, 4)
        scored.append((score, title_hits, abstract_hits, {k: str(node[k]) for k in ("phylum", "class", "order", "genus")}))

    if not scored:
        return [{"phylum": "Unclassified", "class": "Unclassified", "order": "Unclassified", "genus": "Unclassified"}]

    scored.sort(key=lambda x: (-x[0], -x[1], -x[2], x[3]["phylum"], x[3]["class"]))
    return [tag for *_rest, tag in scored[:limit]]


def load_semantic_topics() -> dict[int, list[dict[str, str]]]:
    if not SEMANTIC_TOPICS_PATH.exists():
        return {}
    rows = json.loads(SEMANTIC_TOPICS_PATH.read_text(encoding="utf-8"))
    topics_by_id: dict[int, list[dict[str, str]]] = {}
    required = {"phylum", "class", "order", "genus"}
    for row in rows:
        paper_id = int(row["id"])
        topics = []
        for topic in row.get("topics", [])[:3]:
            if required <= set(topic):
                topics.append({k: str(topic[k]) for k in ("phylum", "class", "order", "genus")})
        if topics:
            topics_by_id[paper_id] = topics
    return topics_by_id


def load_arxiv_links() -> dict[int, dict[str, str]]:
    if not ARXIV_LINKS_PATH.exists():
        return {}
    rows = json.loads(ARXIV_LINKS_PATH.read_text(encoding="utf-8"))
    links_by_id: dict[int, dict[str, str]] = {}
    for row in rows:
        try:
            paper_id = int(row["id"])
        except (KeyError, TypeError, ValueError):
            continue
        url = str(row.get("url") or "")
        if not url.startswith("https://arxiv.org/abs/"):
            continue
        links_by_id[paper_id] = {
            "url": url,
            "arxiv_id": str(row.get("arxiv_id") or ""),
            "source": str(row.get("source") or ""),
            "confidence": str(row.get("confidence") or ""),
            "matched_title": str(row.get("matched_title") or ""),
        }
    return links_by_id


def normalize_records(raw: list[dict[str, str]], semantic_topics: dict[int, list[dict[str, str]]] | None = None) -> list[dict[str, object]]:
    semantic_topics = semantic_topics or {}
    arxiv_links = load_arxiv_links()
    papers = []
    for idx, item in enumerate(raw, 1):
        authors = split_semicolon(item.get("authors", ""))
        institutions = unique_ordered([canonical_affiliation(aff) for aff in split_institutions(item.get("institutions", ""))])
        institution_regions = [{"affiliation": aff, "region": country_for(aff)} for aff in institutions]
        countries = sorted({x["region"] for x in institution_regions}) or ["Other"]
        title = item.get("title", "").strip()
        abstract = item.get("abstract", "").strip()
        topics = semantic_topics.get(idx) or classify(title, abstract, limit=3)
        arxiv = arxiv_links.get(idx, {})
        papers.append({
            "id": idx,
            "title": title,
            "type": item.get("type", "poster").strip().lower(),
            "authors": authors,
            "institutions": institutions,
            "institution_regions": institution_regions,
            "countries": countries,
            "abstract": abstract,
            "topics": topics,
            "primary_phylum": topics[0]["phylum"],
            "primary_class": topics[0]["class"],
            "primary_genus": topics[0]["genus"],
            "author_count": len(authors),
            "institution_count": len(institutions),
            "paper_url": arxiv.get("url", ""),
            "paper_arxiv_id": arxiv.get("arxiv_id", ""),
            "paper_source": arxiv.get("source", ""),
            "paper_confidence": arxiv.get("confidence", ""),
        })
    return papers


def make_tree(papers: list[dict[str, object]]) -> dict[str, object]:
    root: dict[str, object] = {"name": "CVPR 2026", "count": len(papers), "children": []}
    phyla: dict[str, dict[str, object]] = {}
    for paper in papers:
        seen_phyla = set()
        seen_classes = set()
        seen_orders = set()
        seen_genera = set()
        for topic in paper["topics"]:  # type: ignore[index]
            ph = topic["phylum"]
            cl = topic["class"]
            od = topic["order"]
            ge = topic["genus"]
            ph_node = phyla.setdefault(ph, {"name": ph, "count": 0, "children": {}})
            if ph not in seen_phyla:
                ph_node["count"] = int(ph_node["count"]) + 1
                seen_phyla.add(ph)
            classes = ph_node["children"]
            assert isinstance(classes, dict)
            cl_node = classes.setdefault(cl, {"name": cl, "count": 0, "children": {}})
            class_key = (ph, cl)
            if class_key not in seen_classes:
                cl_node["count"] = int(cl_node["count"]) + 1
                seen_classes.add(class_key)
            orders = cl_node["children"]
            assert isinstance(orders, dict)
            od_node = orders.setdefault(od, {"name": od, "count": 0, "children": {}})
            order_key = (ph, cl, od)
            if order_key not in seen_orders:
                od_node["count"] = int(od_node["count"]) + 1
                seen_orders.add(order_key)
            genera = od_node["children"]
            assert isinstance(genera, dict)
            ge_node = genera.setdefault(ge, {"name": ge, "count": 0, "children": []})
            genus_key = (ph, cl, od, ge)
            if genus_key not in seen_genera:
                ge_node["count"] = int(ge_node["count"]) + 1
                seen_genera.add(genus_key)

    def finish(node: dict[str, object]) -> dict[str, object]:
        children = node.get("children")
        if isinstance(children, dict):
            node["children"] = [finish(c) for c in sorted(children.values(), key=lambda x: (-int(x["count"]), str(x["name"])))]
        return node

    root["children"] = [finish(c) for c in sorted(phyla.values(), key=lambda x: (-int(x["count"]), str(x["name"])))]
    return root


def count_topic(papers: list[dict[str, object]], level: str) -> list[tuple[str, int]]:
    c = Counter()
    for paper in papers:
        seen = {topic[level] for topic in paper["topics"]}  # type: ignore[index]
        c.update(seen)
    return c.most_common()


def build_html() -> str:
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    semantic_topics = load_semantic_topics()
    papers = normalize_records(raw, semantic_topics)
    tree = make_tree(papers)

    type_counts = Counter(p["type"] for p in papers)
    phylum_counts = count_topic(papers, "phylum")
    class_counts = count_topic(papers, "class")
    genus_counts = count_topic(papers, "genus")
    country_counts = Counter(c for p in papers for c in set(p["countries"]))  # type: ignore[arg-type]
    aff_counts = Counter(a for p in papers for a in set(p["institutions"]))  # type: ignore[arg-type]
    author_slots = sum(int(p["author_count"]) for p in papers)
    abstracted = sum(1 for p in papers if p["abstract"])

    payload = {
        "papers": papers,
        "tree": tree,
        "summary": {
            "parsed": len(papers),
            "type_counts": dict(type_counts),
            "phylum_counts": phylum_counts,
            "class_counts": class_counts,
            "genus_counts": genus_counts,
            "country_counts": country_counts.most_common(),
            "aff_counts": aff_counts.most_common(60),
            "author_slots": author_slots,
            "abstracted": abstracted,
            "topic_source": "semantic-agent" if semantic_topics else "keyword-fallback",
            "semantic_topic_count": len(semantic_topics),
            "arxiv_link_count": sum(1 for p in papers if p.get("paper_url")),
            "official": OFFICIAL_STATS,
        },
    }
    payload_json = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).replace("</", "<\\/")

    return HTML_TEMPLATE.replace("__DATA_JSON__", payload_json)


def build_methodology_html() -> str:
    semantic_topics = load_semantic_topics()
    total = len(json.loads(DATA_PATH.read_text(encoding="utf-8")))
    topic_lengths = [len(v) for v in semantic_topics.values()] or [0]
    phylum_counts = Counter(ph for topics in semantic_topics.values() for ph in {topic["phylum"] for topic in topics})
    top_phyla = phylum_counts.most_common(12)
    taxonomy_rows = [
        f"<tr><td>{escape(str(node['phylum']))}</td><td>{escape(str(node['class']))}</td><td>{escape(str(node['order']))}</td><td>{escape(str(node['genus']))}</td></tr>"
        for node in TAXONOMY
    ]
    top_rows = [
        f"<tr><td>{escape(label)}</td><td>{count:,}</td></tr>"
        for label, count in top_phyla
    ]
    chunk_rows = [
        ("01", "1-679", "679"),
        ("02", "680-1358", "679"),
        ("03", "1359-2037", "679"),
        ("04", "2038-2716", "679"),
        ("05", "2717-3395", "679"),
        ("06", "3396-4070", "675"),
    ]
    chunk_html = "".join(f"<tr><td>Agent {n}</td><td>{ids}</td><td>{count}</td></tr>" for n, ids, count in chunk_rows)
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>CVPR 2026 Semantic Topic Methodology</title>
<style>
:root{{--bg:#f5f5f7;--panel:#fff;--text:#1d1d1f;--text-2:#424245;--muted:#6e6e73;--border:#d2d2d7;--border-soft:#e5e5ea;--accent:#0066cc;--accent-soft:#eef5ff;--font:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:var(--font);font-size:15px;line-height:1.62}}main{{max-width:980px;margin:0 auto;padding:42px 24px 80px}}a{{color:var(--accent);text-decoration:none}}a:hover{{text-decoration:underline}}.top{{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:28px}}.back{{border:1px solid var(--border-soft);background:var(--panel);border-radius:999px;padding:6px 12px;font-size:13px}}h1{{font-size:42px;line-height:1.08;margin:0 0 12px;letter-spacing:-.03em}}h2{{font-size:22px;margin:30px 0 8px;letter-spacing:-.02em}}p{{color:var(--text-2);margin:8px 0}}.lede{{font-size:18px;max-width:820px}}.card{{background:var(--panel);border:1px solid var(--border-soft);border-radius:10px;padding:18px;margin:16px 0}}.grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}}.stat{{background:var(--accent-soft);border:1px solid rgba(0,102,204,.12);border-radius:8px;padding:12px}}.stat .v{{font-size:24px;font-weight:700;color:var(--accent)}}.stat .l{{font-size:11px;text-transform:uppercase;color:var(--muted);letter-spacing:.06em}}ul{{padding-left:20px;color:var(--text-2)}}li{{margin:6px 0}}table{{width:100%;border-collapse:collapse;background:var(--panel);font-size:14px}}th,td{{border-bottom:1px solid var(--border-soft);padding:8px 10px;text-align:left;vertical-align:top}}th{{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);background:#fbfbfd}}code{{background:var(--accent-soft);color:var(--accent);border-radius:5px;padding:1px 5px}}.note{{font-size:13px;color:var(--muted)}}@media(max-width:720px){{.grid{{grid-template-columns:1fr 1fr}}h1{{font-size:34px}}.top{{align-items:flex-start;flex-direction:column}}}}
</style>
</head>
<body>
<main>
  <div class="top"><a class="back" href="cvpr2026_explorer.html">Back to explorer</a><span class="note">Generated with the local CVPR 2026 explorer build</span></div>
  <h1>Semantic Topic Tagging Methodology</h1>
  <p class="lede">이 문서는 CVPR 2026 Paper Explorer의 계통도(topic phylogeny)가 어떻게 만들어졌는지 정리한 방법론이다. 초기 키워드 매칭 방식은 폐기하고, 논문별 title과 abstract를 의미론적으로 읽어 최대 3개의 연구분야 태그를 부여했다.</p>

  <div class="grid">
    <div class="stat"><div class="v">{total:,}</div><div class="l">Papers</div></div>
    <div class="stat"><div class="v">{len(semantic_topics):,}</div><div class="l">Semantic tagged</div></div>
    <div class="stat"><div class="v">{max(topic_lengths)}</div><div class="l">Max tags/paper</div></div>
    <div class="stat"><div class="v">{sum(1 for topics in semantic_topics.values() if topics and topics[0]['phylum'] == 'Unclassified'):,}</div><div class="l">Unclassified</div></div>
  </div>

  <h2>1. Input</h2>
  <div class="card">
    <p>각 논문은 CVPR 2026 paper JSON에서 추출한 <code>title</code>, <code>abstract</code>, <code>type</code>을 기준으로 분류했다. 저자명, 소속, 국가 정보는 topic 판단에 사용하지 않았다.</p>
  </div>

  <h2>2. Taxonomy</h2>
  <div class="card">
    <p>라벨 체계는 CVML Paper Phylogeny 스타일을 따라 4단계로 고정했다: <code>phylum -> class -> order -> genus</code>. 에이전트는 자유 라벨을 만들지 않고 아래 허용 라벨 중에서만 선택했다.</p>
    <table><thead><tr><th>Phylum</th><th>Class</th><th>Order</th><th>Genus</th></tr></thead><tbody>{''.join(taxonomy_rows)}</tbody></table>
  </div>

  <h2>3. Six-Agent Annotation</h2>
  <div class="card">
    <p>전체 4,070편을 여섯 구간으로 나누고, 각 에이전트가 자기 구간의 초록을 읽어 독립적으로 분류했다.</p>
    <table><thead><tr><th>Worker</th><th>Paper IDs</th><th>Papers</th></tr></thead><tbody>{chunk_html}</tbody></table>
  </div>

  <h2>4. Decision Rules</h2>
  <div class="card">
    <ul>
      <li>키워드가 보인다는 이유만으로 태그하지 않고, 논문의 주된 문제 설정과 기여를 우선했다.</li>
      <li>방법론 단어보다 실제 task/domain을 우선했다. 예를 들어 diffusion을 도구로 쓴 medical segmentation 논문은 medical/segmentation 성격을 함께 고려했다.</li>
      <li>각 논문은 최소 1개, 최대 3개 topic만 가진다.</li>
      <li>여러 분야가 동등하게 중요하면 primary task, application domain, method family 순서로 우선순위를 두었다.</li>
      <li>정말 맞는 taxonomy가 없을 때만 <code>Unclassified</code>를 사용했다.</li>
    </ul>
  </div>

  <h2>5. Merge Validation</h2>
  <div class="card">
    <p>여섯 결과 파일은 <code>scripts/merge_semantic_topics.py</code>로 병합했다. 병합 단계에서 모든 paper id가 정확히 한 번씩 존재하는지, topic 수가 3개 이하인지, 모든 라벨이 허용 taxonomy 안에 있는지 검증했다.</p>
  </div>

  <h2>6. Result Snapshot</h2>
  <div class="card">
    <table><thead><tr><th>Top phylum</th><th>Tagged paper count</th></tr></thead><tbody>{''.join(top_rows)}</tbody></table>
  </div>

  <h2>7. Limitations</h2>
  <div class="card">
    <p>이 분류는 논문 원문 전체가 아니라 title과 abstract만 사용한 탐색용 의미론적 태깅이다. 세부 subfield의 미묘한 차이, 저자 의도, 벤치마크 중심 논문과 방법론 중심 논문의 경계는 완벽히 반영하지 못할 수 있다. 따라서 이 계통도는 정밀 bibliometric ground truth라기보다 CVPR 2026 논문군의 연구 흐름을 빠르게 탐색하기 위한 지도에 가깝다.</p>
  </div>
</main>
</body>
</html>
"""


def md_escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def build_affiliation_rankings_md() -> str:
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    papers = normalize_records(raw, load_semantic_topics())
    country_counts = Counter(c for p in papers for c in set(p["countries"]))  # type: ignore[arg-type]
    aff_counts = Counter(a for p in papers for a in set(p["institutions"]))  # type: ignore[arg-type]
    aff_region: dict[str, str] = {}
    for paper in papers:
        for item in paper["institution_regions"]:  # type: ignore[index]
            aff_region.setdefault(str(item["affiliation"]), str(item["region"]))

    lines = [
        "# CVPR 2026 Affiliation Rankings",
        "",
        "Counts are computed from the explorer-normalized paper list. Each paper contributes at most once to a given affiliation or region.",
        "",
        f"- Papers parsed: {len(papers):,}",
        f"- Unique affiliations: {len(aff_counts):,}",
        f"- Affiliation regions: {len(country_counts):,}",
        "",
        "## Affiliation Regions",
        "",
        "| Rank | Region | Papers |",
        "|---:|---|---:|",
    ]
    for rank, (region, count) in enumerate(country_counts.most_common(), 1):
        lines.append(f"| {rank} | {md_escape(region)} | {count:,} |")

    lines.extend([
        "",
        "## Top Affiliations",
        "",
        "| Rank | Affiliation | Region | Papers |",
        "|---:|---|---|---:|",
    ])
    for rank, (aff, count) in enumerate(aff_counts.most_common(), 1):
        lines.append(f"| {rank} | {md_escape(aff)} | {md_escape(aff_region.get(aff, 'Other'))} | {count:,} |")

    lines.extend([
        "",
        "## Notes",
        "",
        "- Affiliation strings are normalized by semicolon splitting, selected compound-affiliation splitting, and per-paper deduplication.",
        "- Region assignment uses manual correction rules first, then `classification/aff_region_table.json`, then fallback country hints.",
        "- Counts are exploratory metadata for the CVPR 2026 explorer, not official institutional statistics.",
        "",
    ])
    return "\n".join(lines)


def affiliation_ranking_data() -> tuple[list[dict[str, object]], list[dict[str, object]], int, int]:
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    papers = normalize_records(raw, load_semantic_topics())
    country_counts = Counter(c for p in papers for c in set(p["countries"]))  # type: ignore[arg-type]
    aff_counts = Counter(a for p in papers for a in set(p["institutions"]))  # type: ignore[arg-type]
    aff_region: dict[str, str] = {}
    for paper in papers:
        for item in paper["institution_regions"]:  # type: ignore[index]
            aff_region.setdefault(str(item["affiliation"]), str(item["region"]))
    regions = [{"rank": i, "region": region, "papers": count} for i, (region, count) in enumerate(country_counts.most_common(), 1)]
    affiliations = [{"rank": i, "affiliation": aff, "region": aff_region.get(aff, "Other"), "papers": count} for i, (aff, count) in enumerate(aff_counts.most_common(), 1)]
    return regions, affiliations, len(papers), len(aff_counts)


def build_affiliation_rankings_html() -> str:
    regions, affiliations, paper_count, aff_count = affiliation_ranking_data()
    region_rows = "\n".join(
        f"<tr><td>{row['rank']}</td><td>{escape(str(row['region']))}</td><td>{int(row['papers']):,}</td></tr>"
        for row in regions
    )
    aff_rows = "\n".join(
        f"<tr><td>{row['rank']}</td><td>{escape(str(row['affiliation']))}</td><td>{escape(str(row['region']))}</td><td>{int(row['papers']):,}</td></tr>"
        for row in affiliations
    )
    top_region = regions[0] if regions else {"region": "-", "papers": 0}
    top_aff = affiliations[0] if affiliations else {"affiliation": "-", "papers": 0}
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Explorer-Normalized CVPR 2026 Affiliation/Region Statistics</title>
<style>
:root{{--bg:#f5f5f7;--panel:#fff;--text:#1d1d1f;--text-2:#424245;--muted:#6e6e73;--border:#d2d2d7;--border-soft:#e5e5ea;--accent:#0066cc;--accent-soft:#eef5ff;--font:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:var(--font);font-size:15px;line-height:1.55}}main{{max-width:1180px;margin:0 auto;padding:40px 24px 80px}}a{{color:var(--accent);text-decoration:none}}a:hover{{text-decoration:underline}}.top{{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:28px}}.back{{border:1px solid var(--border-soft);background:var(--panel);border-radius:999px;padding:6px 12px;font-size:13px}}h1{{font-size:42px;line-height:1.08;margin:0 0 10px;letter-spacing:-.03em}}h2{{font-size:22px;margin:0 0 12px}}p{{color:var(--text-2);margin:8px 0}}.lede{{font-size:18px;max-width:860px}}.grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:22px 0}}.stat,.card{{background:var(--panel);border:1px solid var(--border-soft);border-radius:10px;box-shadow:0 1px 2px rgba(0,0,0,.04)}}.stat{{padding:16px}}.stat .v{{font-size:27px;font-weight:700;color:var(--accent)}}.stat .l{{font-size:11px;text-transform:uppercase;color:var(--muted);letter-spacing:.06em}}.card{{padding:18px;margin:18px 0}}.tables{{display:grid;grid-template-columns:390px minmax(0,1fr);gap:18px;align-items:start}}.table-wrap{{max-height:760px;overflow:auto;border:1px solid var(--border-soft);border-radius:8px}}table{{width:100%;border-collapse:collapse;background:var(--panel);font-size:14px}}th,td{{border-bottom:1px solid var(--border-soft);padding:8px 10px;text-align:left;vertical-align:top}}th{{position:sticky;top:0;background:#fbfbfd;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em;z-index:1}}td:first-child,td:last-child{{font-variant-numeric:tabular-nums;white-space:nowrap}}tr:hover td{{background:var(--accent-soft)}}.note{{font-size:13px;color:var(--muted)}}@media(max-width:900px){{.grid,.tables{{grid-template-columns:1fr}}h1{{font-size:34px}}.top{{align-items:flex-start;flex-direction:column}}}}
</style>
</head>
<body>
<main>
  <div class="top"><a class="back" href="cvpr2026_explorer.html">Back to explorer</a><span><a class="back" href="cvpr2026_other_affiliations.html" target="_blank" rel="noopener">Other review list</a> <a class="back" href="cvpr2026_affiliation_rankings.md" target="_blank" rel="noopener">Markdown</a></span></div>
  <h1>Explorer-Normalized CVPR 2026 Affiliation/Region Statistics</h1>
  <p class="lede">Full affiliation and region rankings computed from the explorer-normalized paper list. Counts are per-paper unique affiliations or regions.</p>
  <div class="grid">
    <div class="stat"><div class="v">{paper_count:,}</div><div class="l">Papers</div></div>
    <div class="stat"><div class="v">{aff_count:,}</div><div class="l">Affiliations</div></div>
    <div class="stat"><div class="v">{escape(str(top_region['region']))}</div><div class="l">Top region · {int(top_region['papers']):,}</div></div>
    <div class="stat"><div class="v">{escape(str(top_aff['affiliation']))}</div><div class="l">Top affiliation · {int(top_aff['papers']):,}</div></div>
  </div>
  <div class="tables">
    <section class="card">
      <h2>Affiliation Regions</h2>
      <div class="table-wrap"><table><thead><tr><th>Rank</th><th>Region</th><th>Papers</th></tr></thead><tbody>{region_rows}</tbody></table></div>
    </section>
    <section class="card">
      <h2>Top Affiliations</h2>
      <div class="table-wrap"><table><thead><tr><th>Rank</th><th>Affiliation</th><th>Region</th><th>Papers</th></tr></thead><tbody>{aff_rows}</tbody></table></div>
    </section>
  </div>
  <p class="note">Region assignment uses manual correction rules first, then <code>classification/aff_region_table.json</code>, then fallback country hints. These are exploratory metadata, not official institutional statistics.</p>
</main>
</body>
</html>
"""


def other_affiliation_rows() -> tuple[list[dict[str, object]], int]:
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    papers = normalize_records(raw, load_semantic_topics())
    counts: Counter[str] = Counter()
    for paper in papers:
        seen = {
            str(item["affiliation"])
            for item in paper["institution_regions"]  # type: ignore[index]
            if item["region"] == "Other"
        }
        counts.update(seen)
    rows = [{"rank": i, "affiliation": aff, "papers": count} for i, (aff, count) in enumerate(counts.most_common(), 1)]
    return rows, len(papers)


def build_other_affiliations_md() -> str:
    rows, paper_count = other_affiliation_rows()
    lines = [
        "# CVPR 2026 Other Affiliation Review List",
        "",
        "Affiliations below are still mapped to `Other` after the current correction rules. Counts are per-paper unique occurrences.",
        "",
        f"- Papers parsed: {paper_count:,}",
        f"- Other affiliations: {len(rows):,}",
        "",
        "| Rank | Affiliation | Papers |",
        "|---:|---|---:|",
    ]
    for row in rows:
        lines.append(f"| {row['rank']} | {md_escape(row['affiliation'])} | {int(row['papers']):,} |")
    lines.append("")
    return "\n".join(lines)


def build_other_affiliations_html() -> str:
    rows, paper_count = other_affiliation_rows()
    table_rows = "\n".join(
        f"<tr><td>{row['rank']}</td><td>{escape(str(row['affiliation']))}</td><td>{int(row['papers']):,}</td></tr>"
        for row in rows
    )
    top = rows[0] if rows else {"affiliation": "-", "papers": 0}
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>CVPR 2026 Other Affiliation Review List</title>
<style>
:root{{--bg:#f5f5f7;--panel:#fff;--text:#1d1d1f;--text-2:#424245;--muted:#6e6e73;--border-soft:#e5e5ea;--accent:#0066cc;--accent-soft:#eef5ff;--font:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:var(--font);font-size:15px;line-height:1.55}}main{{max-width:1040px;margin:0 auto;padding:40px 24px 80px}}a{{color:var(--accent);text-decoration:none}}a:hover{{text-decoration:underline}}.top{{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:28px}}.back{{border:1px solid var(--border-soft);background:var(--panel);border-radius:999px;padding:6px 12px;font-size:13px}}h1{{font-size:42px;line-height:1.08;margin:0 0 10px;letter-spacing:-.03em}}p{{color:var(--text-2)}}.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:22px 0}}.stat,.card{{background:var(--panel);border:1px solid var(--border-soft);border-radius:10px;box-shadow:0 1px 2px rgba(0,0,0,.04)}}.stat{{padding:16px}}.stat .v{{font-size:26px;font-weight:700;color:var(--accent)}}.stat .l{{font-size:11px;text-transform:uppercase;color:var(--muted);letter-spacing:.06em}}.card{{padding:18px}}.table-wrap{{max-height:780px;overflow:auto;border:1px solid var(--border-soft);border-radius:8px}}table{{width:100%;border-collapse:collapse;background:var(--panel);font-size:14px}}th,td{{border-bottom:1px solid var(--border-soft);padding:8px 10px;text-align:left;vertical-align:top}}th{{position:sticky;top:0;background:#fbfbfd;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em;z-index:1}}td:first-child,td:last-child{{font-variant-numeric:tabular-nums;white-space:nowrap}}tr:hover td{{background:var(--accent-soft)}}@media(max-width:760px){{.grid{{grid-template-columns:1fr}}h1{{font-size:34px}}.top{{align-items:flex-start;flex-direction:column}}}}
</style>
</head>
<body>
<main>
  <div class="top"><a class="back" href="cvpr2026_affiliation_rankings.html">Back to rankings</a><a class="back" href="cvpr2026_other_affiliations.md" target="_blank" rel="noopener">Markdown</a></div>
  <h1>Other Affiliation Review List</h1>
  <p>Affiliations still mapped to <b>Other</b> after the current correction rules. This is the list to inspect for the next cleanup pass.</p>
  <div class="grid">
    <div class="stat"><div class="v">{paper_count:,}</div><div class="l">Papers</div></div>
    <div class="stat"><div class="v">{len(rows):,}</div><div class="l">Other affiliations</div></div>
    <div class="stat"><div class="v">{escape(str(top['affiliation']))}</div><div class="l">Top remaining · {int(top['papers']):,}</div></div>
  </div>
  <section class="card"><div class="table-wrap"><table><thead><tr><th>Rank</th><th>Affiliation</th><th>Papers</th></tr></thead><tbody>{table_rows}</tbody></table></div></section>
</main>
</body>
</html>
"""


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>CVPR 2026 · Paper Explorer</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>
<script>
window.MathJax = {
  tex: {inlineMath: [["$", "$"], ["\\(", "\\)"]], processEscapes: true},
  options: {skipHtmlTags: ["script", "noscript", "style", "textarea", "pre", "code"]}
};
</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
<style>
:root{
  --bg:#fff;--bg-alt:#f5f5f7;--bg-soft:#fafafa;--panel:#fff;--border:#d2d2d7;--border-soft:#e5e5ea;
  --text:#1d1d1f;--text-2:#424245;--muted:#6e6e73;--muted-2:#86868b;--accent:#0066cc;
  --accent-soft:rgba(0,102,204,.08);--green:#248a3d;--orange:#b25000;--purple:#6e3ad6;
  --shadow:0 1px 3px rgba(0,0,0,.04),0 1px 2px rgba(0,0,0,.06);
  --font:-apple-system,BlinkMacSystemFont,"SF Pro Text","SF Pro Display","Segoe UI","Pretendard","Noto Sans KR",system-ui,sans-serif;
}
*{box-sizing:border-box}html,body{margin:0;padding:0;background:var(--bg);color:var(--text);font-family:var(--font);font-size:15px;line-height:1.47;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.topbar{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.86);backdrop-filter:saturate(180%) blur(20px);border-bottom:1px solid var(--border-soft);height:52px}
.topbar .inner{max-width:1440px;margin:0 auto;padding:0 24px;height:100%;display:flex;align-items:center;gap:18px}
.brand{font-weight:600;font-size:17px;color:inherit;text-decoration:none}.brand .dot{color:var(--accent)}.meta{color:var(--muted);font-size:13px}
.right{margin-left:auto;display:flex;gap:8px;align-items:center}.stat-pill{font-size:12px;color:var(--muted-2);padding:4px 10px;border-radius:999px;background:var(--bg-alt);border:1px solid var(--border-soft);font-variant-numeric:tabular-nums}.stat-pill b{color:var(--text)}.stat-pill.accent{background:var(--accent-soft);color:var(--accent)}.stat-pill.sibling{background:#fff;color:var(--text-2)}.download-json,.method-link,.sibling-link{font-family:var(--font);font-weight:600;cursor:pointer;text-decoration:none}.download-json:hover,.method-link:hover,.sibling-link:hover{border-color:rgba(0,102,204,.35);color:var(--accent);text-decoration:none}
.layout{max-width:1440px;margin:0 auto;padding:0 24px;display:grid;grid-template-columns:240px minmax(0,1fr);gap:32px;align-items:start}
aside{position:sticky;top:64px;padding:28px 0;max-height:calc(100vh - 64px);overflow-y:auto}aside h4{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:18px 0 6px;font-weight:600}aside a{display:block;padding:6px 10px;margin:1px 0;color:var(--text-2);border-radius:6px;font-size:14px;border-left:2px solid transparent}aside a:hover{background:var(--bg-alt);text-decoration:none;color:var(--text)}aside a.active{color:var(--accent);border-left-color:var(--accent);background:var(--accent-soft)}
main{padding:48px 0 80px;min-width:0}section{scroll-margin-top:76px;margin-bottom:64px}.eyebrow{color:var(--muted);font-size:13px;font-weight:600;letter-spacing:.02em;margin-bottom:10px}h1{font-size:56px;line-height:1.05;margin:0 0 16px;letter-spacing:-.03em}h2{font-size:28px;letter-spacing:-.02em;margin:0 0 8px}h3{font-size:16px;margin:0 0 10px}.lede{font-size:20px;line-height:1.42;color:var(--text-2);max-width:860px}.section-sub{color:var(--muted);font-size:14px;margin-bottom:14px}.disclaimer{margin:0 0 14px;padding:10px 12px;border:1px solid rgba(0,102,204,.14);border-radius:8px;background:var(--accent-soft);color:var(--text-2);font-size:13px;line-height:1.48}.pill{display:inline-block;padding:2px 8px;border-radius:999px;background:var(--accent-soft);color:var(--accent);font-size:12px;font-weight:600;vertical-align:middle}
.kpis,.stats-grid,.stat-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.kpi,.stat,.card{background:var(--panel);border:1px solid var(--border-soft);border-radius:8px;padding:18px;box-shadow:var(--shadow)}.kpi.total{border-color:rgba(0,102,204,.22);background:linear-gradient(180deg,#fff,#f8fbff)}.kpi.type-part{border-top:3px solid rgba(0,102,204,.16)}.kpi-role{display:inline-flex;align-items:center;height:20px;margin-bottom:10px;padding:0 7px;border-radius:999px;background:var(--bg-alt);border:1px solid var(--border-soft);color:var(--muted);font-size:10px;font-weight:700;letter-spacing:.08em}.kpi.total .kpi-role{background:var(--accent-soft);border-color:rgba(0,102,204,.18);color:var(--accent)}.kpi .v,.stat .v{font-size:28px;font-weight:700;letter-spacing:-.02em}.kpi .l,.stat .l{font-size:11px;text-transform:uppercase;color:var(--muted);letter-spacing:.06em}.kpi .note,.stat .desc{font-size:12px;color:var(--muted);margin-top:6px}.kpi-equation{grid-column:1/-1;display:grid;grid-template-columns:auto 1fr;align-items:center;gap:14px;padding:10px 14px;border:1px solid rgba(0,102,204,.16);background:var(--accent-soft);border-radius:8px;color:var(--text-2);font-size:13px}.kpi-equation span{font-weight:700;color:var(--accent);white-space:nowrap}.kpi-equation b{color:var(--text);font-variant-numeric:tabular-nums}.accent{color:var(--accent)}.green{color:var(--green)}.orange{color:var(--orange)}.purple{color:var(--purple)}
.stats-hero{background:linear-gradient(180deg,#fbfbfd,#fff);border:1px solid var(--border-soft);border-radius:10px;padding:20px;box-shadow:var(--shadow)}.accept-bar{margin-top:16px}.accept-bar .row{display:flex;align-items:center;gap:10px;color:var(--text-2);font-size:13px}.track{height:8px;flex:1;background:var(--bg-alt);border-radius:999px;overflow:hidden}.fill{height:100%;background:linear-gradient(90deg,var(--accent),#34c759);border-radius:999px}.footnote{margin-top:14px;color:var(--muted);font-size:13px}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:16px}.card-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}.tabs{display:inline-flex;background:var(--bg-alt);border:1px solid var(--border-soft);border-radius:8px;padding:2px}.tab{background:transparent;border:0;padding:5px 11px;font-size:12px;color:var(--muted);border-radius:6px;cursor:pointer;font-family:var(--font);font-weight:500}.tab.active{background:#fff;color:var(--text);box-shadow:var(--shadow)}
.chart-box{height:420px}.chart-box.mini{height:240px}.chart-box.tall{height:560px}.chart-box.short{height:300px}.chart-box.xtall{height:720px}
.method-actions{margin:10px 0 14px}.method-actions .method-link{display:inline-block;color:var(--accent);background:var(--accent-soft);border-color:rgba(0,102,204,.18)}.tree-panel{display:grid;grid-template-columns:360px minmax(0,1fr);gap:16px}.tree-list{font-size:13px;max-height:680px;overflow:auto;padding-right:6px}.tree-node{border-left:1px solid var(--border-soft);margin-left:9px;padding-left:10px}.tree-row{display:flex;align-items:center;gap:8px;padding:5px 6px;border-radius:6px;cursor:pointer}.tree-row:hover{background:var(--bg-alt)}.tree-row b{font-weight:600}.tree-count{margin-left:auto;color:var(--muted);font-variant-numeric:tabular-nums}.tree-dot{width:8px;height:8px;border-radius:50%;background:var(--accent);flex:0 0 auto}.lineage{display:flex;flex-wrap:wrap;gap:8px}.lineage .crumb{padding:8px 10px;border:1px solid var(--border-soft);border-radius:8px;background:var(--bg-soft);font-size:13px}
.heatmap{min-width:980px}.heat-row{display:grid;grid-template-columns:150px repeat(var(--cols),minmax(48px,1fr));align-items:stretch}.heat-cell{min-height:34px;border:1px solid #fff;background:var(--bg-alt);font-size:11px;display:flex;align-items:center;justify-content:center;color:var(--text-2);cursor:pointer}.heat-head{font-weight:600;color:var(--muted);background:#fff;writing-mode:vertical-rl;text-orientation:mixed;height:120px;justify-content:flex-end;padding-bottom:8px}.heat-label{justify-content:flex-start;padding-left:8px;font-weight:600;background:#fff;color:var(--text)}
.plot3d-panel{margin-top:16px;background:linear-gradient(180deg,#fbfbfd,#fff);border:1px solid var(--border-soft);border-radius:8px;padding:14px;box-shadow:var(--shadow)}.plot3d-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:10px}.plot3d-head h3{margin:0}.plot3d-note{color:var(--muted);font-size:12px}.plot3d-shell{position:relative;height:500px;border:1px solid var(--border-soft);border-radius:8px;background:linear-gradient(180deg,#f7f9fc,#eef2f7);overflow:hidden}.plot3d-shell canvas{display:block;width:100%;height:100%;cursor:grab}.plot3d-shell canvas:active{cursor:grabbing}.plot3d-fallback{height:100%;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:13px}.plot3d-tooltip{position:absolute;pointer-events:none;z-index:2;padding:6px 8px;border-radius:6px;background:rgba(29,29,31,.88);color:#fff;font-size:12px;line-height:1.35;opacity:0;transform:translate(10px,10px);white-space:nowrap}.plot3d-legend{display:flex;gap:12px;flex-wrap:wrap;margin-top:8px;color:var(--muted);font-size:12px}
.toolbar{background:var(--bg-soft);border:1px solid var(--border-soft);border-radius:10px;padding:12px;margin-top:12px}.toolbar-row{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0}input,select,button{font-family:var(--font)}input,select{height:36px;border:1px solid var(--border);border-radius:8px;background:#fff;padding:0 10px;font-size:14px;color:var(--text)}input{min-width:220px;flex:1}.btn-clear{height:36px;border:1px solid var(--border);border-radius:8px;background:#fff;padding:0 12px;color:var(--text);cursor:pointer}.btn-clear:hover{background:var(--bg-alt)}
.active-filters{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}.filter-chip{border:1px solid rgba(0,102,204,.18);background:var(--accent-soft);color:var(--accent);border-radius:999px;padding:3px 9px;font-size:12px;cursor:pointer}.filter-chip:hover{border-color:rgba(0,102,204,.35);background:#e8f0ff}.filter-chip::after{content:" ×";color:var(--muted)}.count{margin-left:auto;color:var(--muted);font-size:13px;align-self:center}
.papers{display:grid;gap:10px;margin-top:14px}.paper{border:1px solid var(--border-soft);background:#fff;border-radius:8px;padding:15px 16px}.paper:hover{border-color:var(--border);box-shadow:var(--shadow)}.paper .meta{display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}.paper .badge{padding:2px 8px;border-radius:999px;background:var(--bg-alt);border:1px solid var(--border-soft);font-weight:600}.paper .badge.oral{background:rgba(191,90,242,.10);color:#6e3ad6}.paper .badge.highlight{background:rgba(255,159,10,.12);color:#9a5a00}.paper-link{display:inline-flex;align-items:center;height:20px;padding:0 8px;border-radius:999px;background:var(--accent);border:1px solid var(--accent);color:#fff;font-size:11px;font-weight:700;letter-spacing:.04em;text-decoration:none}.paper-link:hover{background:#0055ad;color:#fff;text-decoration:none}.paper .title{font-size:15.5px;font-weight:600;line-height:1.38;margin-top:8px;cursor:pointer}.paper .authors,.paper .affs{font-size:13px;color:var(--text-2);margin-top:7px;line-height:1.55}.paper .affs{color:var(--muted)}.clickable-token{display:inline;border-radius:5px;padding:1px 3px;cursor:pointer}.clickable-token:hover{background:var(--accent-soft);color:var(--accent)}.clickable-token.matched{background:var(--accent-soft);color:var(--accent);font-weight:600}.sep{color:var(--border);margin:0 2px}.paper mark{background:rgba(255,196,0,.32);padding:0 2px;border-radius:3px}.abstract{display:none;margin-top:10px;padding:12px 14px;background:var(--bg-soft);border-left:3px solid var(--accent);border-radius:0 8px 8px 0;font-size:13.5px;color:var(--text-2);line-height:1.6}.paper.open .abstract{display:block}.topics{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}.topic-chip{font-size:11.5px;padding:2px 8px;border:1px solid var(--border-soft);border-radius:999px;background:#fff;color:var(--text-2);cursor:pointer}.topic-chip:hover{border-color:var(--accent);color:var(--accent)}.topic-chip.matched{background:var(--accent-soft);border-color:rgba(0,102,204,.32);color:var(--accent);font-weight:600}
.pager{display:flex;gap:8px;align-items:center;justify-content:center;margin-top:18px;color:var(--muted)}footer{border-top:1px solid var(--border-soft);padding-top:20px;color:var(--muted);font-size:13px}.credit{margin-bottom:4px}
@media(max-width:1100px){.layout{grid-template-columns:1fr}.right .stat-pill:not(.accent):not(.download-json){display:none}aside{position:static;max-height:none;padding:14px 0}.kpis,.stats-grid,.stat-grid,.two-col,.tree-panel{grid-template-columns:1fr}.kpi-equation{grid-template-columns:1fr}h1{font-size:42px}.chart-box.tall,.chart-box.xtall{height:520px}}
@media(max-width:640px){.layout{padding:0 12px}.topbar .inner{padding:0 12px}.meta{display:none}.kpi .v,.stat .v{font-size:24px}input{min-width:100%}.count{margin-left:0}.chart-box{height:360px}.chart-box.mini{height:230px}}
</style>
</head>
<body>
<div class="topbar"><div class="inner">
  <a class="brand" id="brandHome" href="#overview">CVPR 2026<span class="dot"> · </span>Paper Explorer</a>
  <div class="meta">Denver · June 3-7, 2026</div>
  <div class="right"><a class="stat-pill sibling sibling-link" href="https://gisbi-kim.github.io/icra2026-explorer/" target="_blank" rel="noopener">Also: ICRA 2026 Explorer</a><a class="stat-pill method-link" href="cvpr2026_semantic_methodology.html" target="_blank" rel="noopener">Method</a><button id="downloadJson" class="stat-pill download-json" type="button">JSON</button><span class="stat-pill"><b>16,092</b> submissions</span><span class="stat-pill"><b>4,090</b> accepted</span><span class="stat-pill accent"><b>25.42%</b> acceptance</span></div>
</div></div>
<div class="layout">
<aside class="sidebar">
  <h4>Overview</h4><a href="#overview" class="active">Introduction</a><a href="#stats">Conference statistics</a>
  <h4>Trends</h4><a href="#types">Paper types</a><a href="#phylogeny">CV/ML phylogeny</a><a href="#topics">Topic distributions</a>
  <h4>EDA</h4><a href="#affiliations">Affiliations</a><a href="#heatmap">Country x phylum</a><a href="#misc">Authors & abstracts</a>
  <h4>Search</h4><a href="#search">Find papers</a>
</aside>
<main>
  <section id="overview">
    <div class="eyebrow">IEEE/CVF Conference on Computer Vision and Pattern Recognition</div>
    <h1>Paper Explorer</h1>
    <p class="lede">Search and explore CVPR 2026 accepted papers with abstracts, paper type labels, affiliation summaries, and a phylogenetic-style CV/ML topic taxonomy inspired by the CVML Paper Phylogeny project.</p>
    <div class="kpis" id="kpis"></div>
  </section>
  <section id="stats">
    <h2>Conference statistics <span class="pill">Official</span></h2>
    <div class="section-sub">Final decisions were released on February 20, 2026. The conference is scheduled for June 3-7, 2026 in Denver, Colorado.</div>
    <div class="stats-hero">
      <div class="stats-grid">
        <div class="stat"><div class="v">16,092</div><div class="l">SUBMISSIONS</div><div class="desc">Total submissions</div></div>
        <div class="stat"><div class="v accent">4,090</div><div class="l">ACCEPTED</div><div class="desc">Accepted papers</div></div>
        <div class="stat"><div class="v green">25.42%</div><div class="l">ACCEPTANCE</div><div class="desc">Highly selective CV/ML venue</div></div>
        <div class="stat"><div class="v orange">1,717</div><div class="l">FINDINGS</div><div class="desc">Recommended for Findings workshop</div></div>
      </div>
      <div class="accept-bar"><div class="row"><b>Acceptance</b><div class="track"><div class="fill" style="width:25.42%"></div></div><span>4,090 / 16,092</span></div></div>
      <div class="footnote" id="parsed-footnote"></div>
    </div>
  </section>
  <section id="types">
    <h2>Paper types</h2>
    <div class="section-sub">The source JSON is normalized into exactly three labels: oral, highlight, poster.</div>
    <div class="two-col"><div class="card"><h3>Type distribution</h3><div class="chart-box mini"><canvas id="typeChart"></canvas></div></div><div class="card"><h3>Acceptance composition</h3><div class="chart-box mini"><canvas id="acceptChart"></canvas></div></div></div>
  </section>
  <section id="phylogeny">
    <h2>CV/ML phylogeny <span class="pill">Auto-tagged</span></h2>
    <div class="section-sub">Inspired by <a href="https://gisbi-kim.github.io/cvml-paper-phylogeny/" target="_blank" rel="noopener">CVML Paper Phylogeny</a>: six semantic annotation agents read titles and abstracts, then assign each paper to a 4-depth tree, Phylum -> Class -> Order -> Genus. Multi-label papers contribute to multiple branches.</div>
    <div class="method-actions"><a class="stat-pill method-link" href="cvpr2026_semantic_methodology.html" target="_blank" rel="noopener">Open semantic tagging methodology</a></div>
    <div class="tree-panel">
      <div class="card"><h3>Interactive lineage tree</h3><div id="treeList" class="tree-list"></div></div>
      <div class="card"><h3 id="lineageTitle">Selected lineage</h3><div class="lineage" id="lineageCrumbs"></div><div class="chart-box tall" style="margin-top:14px"><canvas id="lineageChart"></canvas></div></div>
    </div>
  </section>
  <section id="topics">
    <h2>Topic distributions</h2>
    <div class="section-sub">Click any bar to filter the paper list below.</div>
    <div class="two-col"><div class="card"><h3>Top phyla</h3><div class="chart-box tall"><canvas id="phylumChart"></canvas></div></div><div class="card"><h3>Top classes</h3><div class="chart-box tall"><canvas id="classChart"></canvas></div></div></div>
    <div class="card" style="margin-top:16px"><h3>Top genera</h3><div class="chart-box xtall"><canvas id="genusChart"></canvas></div></div>
  </section>
  <section id="affiliations">
    <h2>Affiliations & regions</h2>
    <div class="section-sub">Institution strings are split from the JSON and regions are inferred with lightweight keyword rules. Counts are per-paper unique affiliations or countries.</div>
    <div class="disclaimer">Affiliation and region statistics were produced using automated parsing and repeated automated/manual review passes to reduce obvious alias and country-mapping errors. The source affiliation strings are noisy, so some institution merges or region assignments may still be incorrect; interpret these rankings as exploratory rather than official statistics.</div>
    <div class="method-actions"><a class="stat-pill method-link" href="cvpr2026_affiliation_rankings.html" target="_blank" rel="noopener">Open full rankings</a></div>
    <div class="two-col"><div class="card"><h3>Top affiliations</h3><div class="chart-box tall"><canvas id="affChart"></canvas></div></div><div class="card"><h3>Affiliation regions</h3><div class="chart-box tall"><canvas id="countryChart"></canvas></div></div></div>
  </section>
  <section id="heatmap">
    <h2>Country x phylum</h2>
    <div class="section-sub">Rows are top affiliation regions, columns are top CV/ML phyla. Click cells or labels to filter.</div>
    <div class="section-sub">Each paper can carry up to three semantic tags, so a multi-tag paper may contribute to multiple phylum columns.</div>
    <div class="card" style="overflow-x:auto"><div id="heatmapGrid" class="heatmap"></div></div>
    <div class="plot3d-panel">
      <div class="plot3d-head"><h3>3D bar view</h3><div class="plot3d-note">Drag to rotate, wheel to zoom, click a bar to filter.</div></div>
      <div id="phylum3dPlot" class="plot3d-shell"><div class="plot3d-tooltip" id="phylum3dTip"></div></div>
      <div class="plot3d-legend"><span>Rows: top affiliation regions</span><span>Columns: top phyla</span><span>Height: paper count</span></div>
    </div>
  </section>
  <section id="misc">
    <h2>Authors & abstracts</h2>
    <div class="card"><div class="stat-grid" id="statGrid"></div><div style="margin-top:18px;border-top:1px solid var(--border-soft);padding-top:14px"><h3>Authors per paper</h3><div class="chart-box short"><canvas id="authorsChart"></canvas></div></div></div>
  </section>
  <section id="search">
    <h2>Find papers</h2>
    <div class="section-sub">Searches title, authors, institutions, abstract, and taxonomy labels. Click a paper title to expand the abstract.</div>
    <div class="toolbar">
      <div class="toolbar-row"><input id="q" placeholder="Search 1: gaussian splatting" /><select id="searchMode"><option value="and">AND</option><option value="or">OR</option></select><input id="q2" placeholder="Search 2" /><input id="q3" placeholder="Search 3" /></div>
      <div class="toolbar-row"><select id="typeFilter"><option value="">All types</option><option value="oral">Oral</option><option value="highlight">Highlight</option><option value="poster">Poster</option></select><select id="phylumFilter"><option value="">All phyla</option></select><select id="classFilter"><option value="">All classes</option></select><select id="countryFilter"><option value="">Aff. region</option></select><select id="affFilter"><option value="">All affiliations</option></select></div>
      <div class="toolbar-row"><select id="sortFilter"><option value="default">Sort: original order</option><option value="title-asc">Title A-Z</option><option value="title-desc">Title Z-A</option><option value="authors-desc"># Authors most</option><option value="authors-asc"># Authors fewest</option><option value="type">Type</option></select><select id="pageSizeFilter"><option value="50">50 / page</option><option value="100">100 / page</option><option value="250">250 / page</option><option value="500">500 / page</option></select><button id="clearFilters" class="btn-clear">Clear</button><span class="count" id="count"></span></div>
    </div>
    <div id="activeFilters" class="active-filters"></div><div class="papers" id="papers"></div><div class="pager" id="pager"></div>
  </section>
  <footer><div class="credit">Made by <a href="https://aprl.dgist.ac.kr" target="_blank" rel="noopener">Giseop Kim</a></div>Source: CVPR 2026 virtual paper list and local JSON. Generated <span id="genDate"></span>.</footer>
</main>
</div>
<script id="app-data" type="application/json">__DATA_JSON__</script>
<script>
const DATA = JSON.parse(document.getElementById("app-data").textContent);
const PAPERS = DATA.papers;
const SUMMARY = DATA.summary;
const TREE = DATA.tree;
const $ = id => document.getElementById(id);
const fmt = n => Number(n||0).toLocaleString();
const titleCase = s => String(s||"").replace(/\b\w/g, c=>c.toUpperCase());
const PALETTE = ["#0066cc","#34c759","#ff9f0a","#bf5af2","#ff375f","#5ac8fa","#ffd60a","#30b0c7","#ac8e68","#64d2ff","#ff6482","#a2845e","#8e8e93","#00a878","#c56cf0","#ff6b6b"];
Chart.defaults.color = "#424245"; Chart.defaults.borderColor = "rgba(0,0,0,.06)"; Chart.defaults.font.family = getComputedStyle(document.documentElement).getPropertyValue("--font");
function arrCounts(list){return list.map(([label,value])=>({label,value}));}
function hasTopic(p, level, val){return !val || p.topics.some(t => t[level] === val);}
function tickHit(chart,e,axis="x"){
  const scale = chart.scales[axis];
  if(!scale) return null;
  const chartArea = chart.chartArea || {};
  const x = e.x ?? e.native?.offsetX, y = e.y ?? e.native?.offsetY;
  if(x == null || y == null) return null;
  const pad = 34;
  if(axis==="x" && (y < chartArea.bottom - 6 || y > scale.bottom + pad || x < scale.left - 8 || x > scale.right + 8)) return null;
  if(axis==="y" && (x < scale.left - pad || x > chartArea.left + 6 || y < scale.top - 8 || y > scale.bottom + 8)) return null;
  const pixels = scale.ticks.map((_,i)=>scale.getPixelForTick(i));
  let idx = -1, best = Infinity;
  pixels.forEach((px,i)=>{ const d=Math.abs((axis==="x"?x:y)-px); if(d<best){best=d;idx=i;} });
  const step = pixels.length > 1 ? Math.abs(pixels[1]-pixels[0]) : 36;
  if(best > Math.max(16, step/2)) return null;
  const tick = scale.ticks[idx] || {};
  return Number.isInteger(tick.value) ? tick.value : idx;
}
function chartBar(id, rows, opts={}){
  const labels = rows.map(r=>r.label), values = rows.map(r=>r.value);
  const colors = opts.colors ? labels.map((label, i)=>opts.colors(label, i)) : labels.map((_,i)=>PALETTE[i%PALETTE.length]);
  return new Chart($(id), {type:"bar", data:{labels,datasets:[{data:values,backgroundColor:colors,borderRadius:4}]}, options:{indexAxis:opts.vertical?"x":"y",maintainAspectRatio:false,onHover:(e,els,chart)=>{const tick = opts.onTickClick && opts.vertical ? tickHit(chart,e,"x") : null; e.native.target.style.cursor=(els.length || tick !== null)?"pointer":"default";},onClick:(e,els,chart)=>{if(els.length && opts.onClick){opts.onClick(labels[els[0].index]);return;} const tick = opts.onTickClick && opts.vertical ? tickHit(chart,e,"x") : null; if(tick !== null) opts.onTickClick(labels[tick]);},plugins:{legend:{display:false},tooltip:{backgroundColor:"#1d1d1f",padding:10,cornerRadius:8,callbacks:opts.tooltipCallbacks||{}}},scales:{y:{ticks:{autoSkip:false,font:{size:11}},grid:{display:false},border:{display:false}},x:{grid:{color:"rgba(0,0,0,.05)"},border:{display:false}}}}});
}
function chartDoughnut(id, rows, opts={}){
  const labels=rows.map(r=>r.label), values=rows.map(r=>r.value);
  const colors = opts.colors ? labels.map((label, i)=>opts.colors(label, i)) : labels.map((_,i)=>PALETTE[i%PALETTE.length]);
  return new Chart($(id),{type:"doughnut",data:{labels,datasets:[{data:values,backgroundColor:colors,borderColor:"#fff",borderWidth:2}]},options:{maintainAspectRatio:false,cutout:"55%",onHover:(e,els)=>e.native.target.style.cursor=els.length?"pointer":"default",onClick:(e,els)=>{if(els.length&&opts.onClick)opts.onClick(labels[els[0].index]);},plugins:{legend:{position:"right",labels:{boxWidth:10,font:{size:11},padding:8}},tooltip:{backgroundColor:"#1d1d1f",padding:10,cornerRadius:8}}}});
}
const typeRows = ["oral","highlight","poster"].map(k=>({label:k,value:SUMMARY.type_counts[k]||0}));
const phylumRows = arrCounts(SUMMARY.phylum_counts).filter(r=>r.label!=="Unclassified");
const classRows = arrCounts(SUMMARY.class_counts).filter(r=>r.label!=="Unclassified").slice(0,30);
const genusRows = arrCounts(SUMMARY.genus_counts).filter(r=>r.label!=="Unclassified").slice(0,45);
const allCountryRows = arrCounts(SUMMARY.country_counts).filter(r=>r.label!=="Other" && r.label!=="Unknown / Independent / Noise" && r.label!=="Cross-region");
const countryRows = allCountryRows.slice(0,15);
const affRows = arrCounts(SUMMARY.aff_counts).slice(0,25);
const COUNTRY_COLOR = new Map(allCountryRows.map((r,i)=>[r.label, PALETTE[i % PALETTE.length]]));
function colorForCountry(country){ return country && country !== "Other" ? (COUNTRY_COLOR.get(country) || "#c7c7cc") : "#c7c7cc"; }
const AFF_COUNTRY = new Map();
for (const p of PAPERS) {
  for (const item of (p.institution_regions || [])) {
    if (!AFF_COUNTRY.has(item.affiliation)) AFF_COUNTRY.set(item.affiliation, item.region);
  }
}
$("lede-count")?.remove;
const oralCount = SUMMARY.type_counts.oral || 0;
const highlightCount = SUMMARY.type_counts.highlight || 0;
const posterCount = SUMMARY.type_counts.poster || 0;
const kpiTop = [
  [fmt(SUMMARY.parsed),"Unique papers","sum of oral, highlight, and poster","total","TOTAL"],
  [fmt(oralCount),"Oral papers","normalized type","type-part","PART"],
  [fmt(highlightCount),"Highlights","normalized type","type-part","PART"],
  [fmt(posterCount),"Posters","normalized type","type-part","PART"],
];
const kpiRest = [
  [fmt(new Set(PAPERS.flatMap(p=>p.authors)).size),"Unique author names","from JSON author strings",""],
  [fmt(new Set(PAPERS.flatMap(p=>p.institutions)).size),"Unique affiliations","from institution strings",""],
  [fmt(countryRows.length),"Top regions shown","country inferred from affiliation",""],
  ["4-depth","Phylogeny","phylum/class/order/genus",""],
];
$("kpis").innerHTML =
  kpiTop.map(([v,l,n,c,r])=>`<div class="kpi ${c}"><div class="kpi-role">${r}</div><div class="v">${v}</div><div class="l">${l}</div><div class="note">${n}</div></div>`).join("") +
  `<div class="kpi-equation"><span>Paper type accounting</span><b>${fmt(oralCount)} oral + ${fmt(highlightCount)} highlight + ${fmt(posterCount)} poster = ${fmt(SUMMARY.parsed)} unique papers</b></div>` +
  kpiRest.map(([v,l,n,c])=>`<div class="kpi ${c}"><div class="v">${v}</div><div class="l">${l}</div><div class="note">${n}</div></div>`).join("");
$("parsed-footnote").innerHTML = `<b>Parsed here: ${fmt(SUMMARY.parsed)} unique papers</b>. The official accepted count is ${fmt(SUMMARY.official.accepted)}; the small gap reflects source-list normalization and oral/poster duplicate removal.`;
$("statGrid").innerHTML = [
  [fmt(SUMMARY.author_slots),"Author slots"],
  [(SUMMARY.author_slots/SUMMARY.parsed).toFixed(2),"Mean authors/paper"],
  [fmt(SUMMARY.abstracted),"Abstracts"],
  [fmt(new Set(PAPERS.flatMap(p=>p.institutions)).size),"Affiliations"],
].map(([v,l])=>`<div class="stat"><div class="v">${v}</div><div class="l">${l}</div></div>`).join("");
chartDoughnut("typeChart", typeRows, {onClick:v=>setFilter("typeFilter",v)});
chartDoughnut("acceptChart", [{label:"Accepted",value:4090},{label:"Rejected / withdrawn",value:16092-4090}], {colors:(label)=>label==="Accepted"?"#0066cc":"#c7c7cc"});
chartBar("phylumChart", phylumRows, {onClick:v=>setFilter("phylumFilter",v)});
chartBar("classChart", classRows, {onClick:v=>setFilter("classFilter",v)});
chartBar("genusChart", genusRows, {onClick:v=>{state.genus = (state.genus === v ? "" : v); page=1; renderResults(); goSearch();}});
chartBar("affChart", affRows, {
  onClick:v=>setFilter("affFilter",v),
  colors:v=>colorForCountry(AFF_COUNTRY.get(v)),
  tooltipCallbacks:{label:ctx=>` ${ctx.parsed.x} papers · ${AFF_COUNTRY.get(ctx.label)||"Other"} · click to toggle`}
});
chartBar("countryChart", countryRows, {onClick:v=>setFilter("countryFilter",v), colors:v=>colorForCountry(v)});
const authorDist = [...PAPERS.reduce((m,p)=>m.set(p.author_count,(m.get(p.author_count)||0)+1),new Map()).entries()].sort((a,b)=>a[0]-b[0]).map(([label,value])=>({label:String(label),value}));
chartBar("authorsChart", authorDist, {vertical:true, colors:()=>"#0066cc", onClick:v=>setAuthorCountFilter(v), onTickClick:v=>setAuthorCountFilter(v)});
let lineageChart;
function renderTree(){
  function nodeHtml(n, depth=0){
    const kids = n.children || [];
    const row = `<div class="tree-row" data-name="${escapeHtml(n.name)}" data-depth="${depth}"><span class="tree-dot" style="opacity:${Math.max(.35,1-depth*.16)}"></span><b>${escapeHtml(n.name)}</b><span class="tree-count">${fmt(n.count)}</span></div>`;
    return `<div class="tree-node">${row}${kids.map(k=>nodeHtml(k,depth+1)).join("")}</div>`;
  }
  $("treeList").innerHTML = nodeHtml(TREE);
  $("treeList").querySelectorAll(".tree-row").forEach(el=>el.addEventListener("click",()=>selectLineage(el.dataset.name)));
  selectLineage("CVPR 2026");
}
function findNode(n,name){ if(n.name===name)return n; for(const c of (n.children||[])){const f=findNode(c,name); if(f)return f;} return null; }
function selectLineage(name){
  const n=findNode(TREE,name)||TREE;
  $("lineageTitle").textContent = n.name;
  $("lineageCrumbs").innerHTML = `<span class="crumb"><b>${escapeHtml(n.name)}</b> · ${fmt(n.count)} tagged papers</span>`;
  const kids=(n.children||[]).slice(0,20).map(c=>({label:c.name,value:c.count}));
  if(lineageChart) lineageChart.destroy();
  lineageChart = chartBar("lineageChart", kids.length?kids:[{label:n.name,value:n.count}], {onClick:v=>selectLineage(v)});
  if(name!=="CVPR 2026" && name!=="Unclassified"){
    const level = ["phylum","class","order","genus"].find(level=>PAPERS.some(p=>p.topics.some(t=>t[level]===name)));
    if(level){ state[level]=name; syncFiltersFromState(); renderResults(); goSearch(); }
  }
}
function heatmapData(){
  const countries = countryRows.slice(0,12).map(r=>r.label);
  const phyla = phylumRows.slice(0,14).map(r=>r.label);
  const values = countries.map(c=>phyla.map(ph=>PAPERS.filter(p=>p.countries.includes(c)&&hasTopic(p,"phylum",ph)).length));
  const max = Math.max(1, ...values.flat());
  return {countries, phyla, values, max};
}
function renderHeatmap(){
  const {countries, phyla, values, max} = heatmapData();
  $("heatmapGrid").style.setProperty("--cols", phyla.length);
  let html = `<div class="heat-row"><div></div>${phyla.map(p=>`<div class="heat-cell heat-head" data-phylum="${escapeHtml(p)}">${escapeHtml(p)}</div>`).join("")}</div>`;
  countries.forEach((c, rowIndex)=>{
    html += `<div class="heat-row"><div class="heat-cell heat-label" data-country="${escapeHtml(c)}">${escapeHtml(c)}</div>`;
    phyla.forEach((ph, colIndex)=>{
      const v = values[rowIndex][colIndex];
      const alpha = Math.sqrt(v/max);
      html += `<div class="heat-cell" data-country="${escapeHtml(c)}" data-phylum="${escapeHtml(ph)}" style="background:rgba(0,102,204,${alpha});color:${alpha>.55?"#fff":"var(--text-2)"}">${v||""}</div>`;
    });
    html += `</div>`;
  });
  $("heatmapGrid").innerHTML = html;
  $("heatmapGrid").querySelectorAll("[data-country],[data-phylum]").forEach(el=>el.addEventListener("click",()=>{
    if(el.dataset.country) $("countryFilter").value=el.dataset.country;
    if(el.dataset.phylum) $("phylumFilter").value=el.dataset.phylum;
    page=1; renderResults(); goSearch();
  }));
}
let phylum3dState;
function render3DPhylumBars(){
  const mount = $("phylum3dPlot"), tip = $("phylum3dTip");
  if(!mount) return;
  if(!window.THREE){
    mount.innerHTML = `<div class="plot3d-fallback">3D view could not load. Check the Three.js CDN connection.</div>`;
    return;
  }
  const {countries, phyla, values, max} = heatmapData();
  const width = Math.max(320, mount.clientWidth), height = Math.max(320, mount.clientHeight);
  mount.querySelectorAll("canvas").forEach(c=>c.remove());
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xf4f7fb);
  scene.fog = new THREE.Fog(0xf4f7fb, 18, 38);
  const camera = new THREE.PerspectiveCamera(34, width / height, 0.1, 1000);
  camera.position.set(8.8, 7.6, 11.4);
  camera.lookAt(0, 1.7, 0);
  const renderer = new THREE.WebGLRenderer({antialias:true, alpha:false});
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  renderer.setSize(width, height);
  if(THREE.SRGBColorSpace) renderer.outputColorSpace = THREE.SRGBColorSpace;
  mount.appendChild(renderer.domElement);
  const group = new THREE.Group();
  group.rotation.x = 0;
  group.rotation.y = -0.68;
  scene.add(group);
  scene.add(new THREE.HemisphereLight(0xffffff, 0xd5dce8, 1.65));
  const keyLight = new THREE.DirectionalLight(0xffffff, 1.05);
  keyLight.position.set(7, 12, 8);
  scene.add(keyLight);
  const gridSize = Math.max(countries.length, phyla.length) + 4;
  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(gridSize + 1.2, gridSize + 1.2),
    new THREE.MeshBasicMaterial({color:0xffffff, transparent:true, opacity:0.72})
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -0.035;
  group.add(floor);
  const grid = new THREE.GridHelper(gridSize, gridSize, 0xbec6d4, 0xe0e5ee);
  grid.position.y = -0.02;
  group.add(grid);
  const bars = [];
  const xStep = 0.72, zStep = 0.72, barW = 0.46;
  const x0 = -((phyla.length - 1) * xStep) / 2;
  const z0 = -((countries.length - 1) * zStep) / 2;
  countries.forEach((country, rowIndex)=>{
    phyla.forEach((phylum, colIndex)=>{
      const value = values[rowIndex][colIndex];
      if(!value) return;
      const h = 0.16 + Math.sqrt(value / max) * 4.8;
      const geo = new THREE.BoxGeometry(barW, h, barW);
      const mat = new THREE.MeshStandardMaterial({color:new THREE.Color(colorForCountry(country)), roughness:0.48, metalness:0.05});
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(x0 + colIndex * xStep, h / 2, z0 + rowIndex * zStep);
      mesh.userData = {country, phylum, value};
      group.add(mesh);
      const edges = new THREE.LineSegments(
        new THREE.EdgesGeometry(geo),
        new THREE.LineBasicMaterial({color:0xffffff, transparent:true, opacity:0.36})
      );
      mesh.add(edges);
      bars.push(mesh);
    });
  });
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  let dragging = false, moved = false, lastX = 0, lastY = 0;
  function render(){ renderer.render(scene, camera); }
  function setPointer(ev){
    const rect = renderer.domElement.getBoundingClientRect();
    pointer.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
  }
  renderer.domElement.addEventListener("pointerdown", ev=>{dragging=true;moved=false;lastX=ev.clientX;lastY=ev.clientY;renderer.domElement.setPointerCapture(ev.pointerId);});
  renderer.domElement.addEventListener("pointermove", ev=>{
    if(dragging){
      const dx = ev.clientX - lastX, dy = ev.clientY - lastY;
      moved = moved || Math.abs(dx) + Math.abs(dy) > 3;
      group.rotation.y += dx * 0.006;
      group.rotation.x = Math.max(-0.42, Math.min(0.18, group.rotation.x + dy * 0.003));
      lastX = ev.clientX; lastY = ev.clientY; render();
      return;
    }
    setPointer(ev);
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(bars, false)[0];
    if(hit){
      const d = hit.object.userData;
      tip.innerHTML = `<b>${escapeHtml(d.country)}</b><br>${escapeHtml(d.phylum)}<br>${fmt(d.value)} papers`;
      tip.style.left = `${ev.offsetX}px`; tip.style.top = `${ev.offsetY}px`; tip.style.opacity = 1;
    } else {
      tip.style.opacity = 0;
    }
  });
  renderer.domElement.addEventListener("pointerup", ev=>{
    dragging=false;
    if(moved) return;
    setPointer(ev);
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(bars, false)[0];
    if(hit){
      const d = hit.object.userData;
      $("countryFilter").value = d.country;
      $("phylumFilter").value = d.phylum;
      page=1; renderResults(); goSearch();
    }
  });
  renderer.domElement.addEventListener("pointerleave", ()=>{dragging=false;tip.style.opacity=0;});
  renderer.domElement.addEventListener("wheel", ev=>{
    ev.preventDefault();
    const scale = ev.deltaY > 0 ? 1.08 : 0.92;
    camera.position.multiplyScalar(scale);
    const dist = camera.position.length();
    if(dist < 7) camera.position.setLength(7);
    if(dist > 26) camera.position.setLength(26);
    camera.lookAt(0,1.7,0);
    render();
  }, {passive:false});
  phylum3dState = {renderer, camera, group, scene};
  render();
}
window.addEventListener("resize",()=>{ if(phylum3dState) render3DPhylumBars(); });
const state = {genus:"",order:"",class:"",phylum:"",author:""};
state.authorCount = "";
let page = 1;
let urlSyncReady = false;
function escapeHtml(s){return String(s||"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[m]));}
function textOf(p){return [p.title,p.type,p.authors.join(" "),p.institutions.join(" "),p.countries.join(" "),p.abstract,p.topics.map(t=>Object.values(t).join(" ")).join(" ")].join(" ").toLowerCase();}
function filterParams(){
  const params = new URLSearchParams();
  for(const [id,key,def=""] of [["q","q"],["q2","q2"],["q3","q3"],["searchMode","mode","and"],["typeFilter","type"],["phylumFilter","phylum"],["classFilter","class"],["countryFilter","country"],["affFilter","aff"],["sortFilter","sort","default"],["pageSizeFilter","pageSize","50"]]){
    const val = $(id)?.value || "";
    if(val && val !== def) params.set(key, val);
  }
  for(const [key,param] of [["author","author"],["authorCount","authorCount"],["order","order"],["genus","genus"]]){
    if(state[key]) params.set(param, state[key]);
  }
  if(page > 1) params.set("page", String(page));
  return params;
}
function replaceUri(hash=location.hash){
  if(!urlSyncReady) return;
  const params = filterParams();
  const qs = params.toString();
  const base = location.href.split(/[?#]/)[0];
  history.replaceState(null, "", `${base}${qs ? "?" + qs : ""}${hash || ""}`);
}
function goSearch(){ replaceUri("#search"); $("search").scrollIntoView({behavior:"smooth", block:"start"}); }
function ensureSelectOption(id,val){
  const el = $(id);
  if(!val || Array.from(el.options).some(o=>o.value===val)) return;
  const o = document.createElement("option");
  o.value = val;
  o.textContent = val;
  el.appendChild(o);
}
function setFilter(id,val){
  ensureSelectOption(id,val);
  const el = $(id);
  el.value = (el.value === val ? "" : val);
  page=1; renderResults(); goSearch();
}
function setAuthorFilter(author){state.author = (state.author === author ? "" : author); page=1; renderResults(); goSearch();}
function setAuthorCountFilter(count){state.authorCount = (state.authorCount === String(count) ? "" : String(count)); page=1; renderResults(); goSearch();}
function syncFiltersFromState(){ if(state.phylum)$("phylumFilter").value=state.phylum; if(state.class)$("classFilter").value=state.class; }
function populateFilters(){
  for(const [id, rows] of [["phylumFilter",phylumRows],["classFilter",classRows],["countryFilter",allCountryRows],["affFilter",affRows]]){
    const el=$(id); rows.forEach(r=>{const o=document.createElement("option");o.value=r.label;o.textContent=`${r.label} (${r.value})`;el.appendChild(o);});
  }
}
function clearFilterState(){
  ["q","q2","q3"].forEach(id=>$(id).value="");
  $("searchMode").value = "and";
  ["typeFilter","phylumFilter","classFilter","countryFilter","affFilter"].forEach(id=>$(id).value="");
  $("sortFilter").value = "default";
  $("pageSizeFilter").value = "50";
  state.genus=state.order=state.class=state.phylum=state.author=state.authorCount="";
  page=1;
}
function applyUriState(){
  clearFilterState();
  const params = new URLSearchParams(location.search);
  for(const [id,key,def=""] of [["q","q"],["q2","q2"],["q3","q3"],["searchMode","mode","and"],["typeFilter","type"],["phylumFilter","phylum"],["classFilter","class"],["countryFilter","country"],["affFilter","aff"],["sortFilter","sort","default"],["pageSizeFilter","pageSize","50"]]){
    const val = params.get(key);
    if(val === null) continue;
    if(["phylumFilter","classFilter","countryFilter","affFilter"].includes(id)) ensureSelectOption(id, val);
    if(Array.from($(id).options || []).length && !Array.from($(id).options).some(o=>o.value===val)) continue;
    $(id).value = val || def;
  }
  for(const [key,param] of [["author","author"],["authorCount","authorCount"],["order","order"],["genus","genus"]]){
    state[key] = params.get(param) || "";
  }
  const requestedPage = Number(params.get("page") || 1);
  page = Number.isFinite(requestedPage) && requestedPage > 0 ? Math.floor(requestedPage) : 1;
}
function filtered(){
  const qs=[$("q").value,$("q2").value,$("q3").value].map(x=>x.trim().toLowerCase()).filter(Boolean);
  const mode=$("searchMode").value, type=$("typeFilter").value, ph=$("phylumFilter").value, cl=$("classFilter").value, country=$("countryFilter").value, aff=$("affFilter").value;
  let rows=PAPERS.filter(p=>{
    if(type && p.type!==type) return false;
    if(ph && !hasTopic(p,"phylum",ph)) return false;
    if(cl && !hasTopic(p,"class",cl)) return false;
    if(state.genus && !hasTopic(p,"genus",state.genus)) return false;
    if(state.order && !hasTopic(p,"order",state.order)) return false;
    if(state.author && !p.authors.includes(state.author)) return false;
    if(state.authorCount && p.author_count !== Number(state.authorCount)) return false;
    if(country && !p.countries.includes(country)) return false;
    if(aff && !p.institutions.includes(aff)) return false;
    if(qs.length){ const hay=textOf(p); const ok=qs.map(q=>hay.includes(q)); if(mode==="and" && !ok.every(Boolean))return false; if(mode==="or" && !ok.some(Boolean))return false; }
    return true;
  });
  const sort=$("sortFilter").value;
  if(sort==="title-asc") rows.sort((a,b)=>a.title.localeCompare(b.title));
  if(sort==="title-desc") rows.sort((a,b)=>b.title.localeCompare(a.title));
  if(sort==="authors-desc") rows.sort((a,b)=>b.author_count-a.author_count);
  if(sort==="authors-asc") rows.sort((a,b)=>a.author_count-b.author_count);
  if(sort==="type") rows.sort((a,b)=>({oral:0,highlight:1,poster:2}[a.type]-{oral:0,highlight:1,poster:2}[b.type]));
  return rows;
}
function mark(s){
  const qs=[$("q").value,$("q2").value,$("q3").value].map(x=>x.trim()).filter(Boolean);
  let out=escapeHtml(s);
  for(const q of qs){ const re=new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")})`,"ig"); out=out.replace(re,"<mark>$1</mark>"); }
  return out;
}
function renderAuthors(p){
  return p.authors.map(a=>`<span class="clickable-token author-token ${state.author===a?"matched":""}" data-author="${escapeHtml(a)}">${mark(a)}</span>`).join(`<span class="sep">;</span>`);
}
function renderAffiliations(p){
  const selectedAff = $("affFilter").value;
  const selectedCountry = $("countryFilter").value;
  return p.institutions.map(a=>{
    const region = AFF_COUNTRY.get(a) || "";
    const matched = (selectedAff && selectedAff === a) || (selectedCountry && selectedCountry === region);
    const title = region ? ` title="${escapeHtml(region)}"` : "";
    return `<span class="clickable-token aff-token ${matched?"matched":""}" data-aff="${escapeHtml(a)}" data-country="${escapeHtml(region)}"${title}>${mark(a)}</span>`;
  }).join(`<span class="sep">;</span>`);
}
function topicMatched(t){
  return ($("phylumFilter").value && t.phylum === $("phylumFilter").value) ||
    ($("classFilter").value && t.class === $("classFilter").value) ||
    (state.order && t.order === state.order) ||
    (state.genus && t.genus === state.genus);
}
function renderTopicChip(t){
  const matched = topicMatched(t) ? " matched" : "";
  return `<span class="topic-chip${matched}" data-phylum="${escapeHtml(t.phylum)}" data-class="${escapeHtml(t.class)}" data-order="${escapeHtml(t.order)}" data-genus="${escapeHtml(t.genus)}">${escapeHtml(t.phylum)} / ${escapeHtml(t.class)}</span>`;
}
function clearActiveFilter(kind,target){
  if(kind==="select") $(target).value = "";
  if(kind==="state") state[target] = "";
  page=1; renderResults();
}
let mathJaxPending = false;
function typesetVisibleMath(){
  if(!window.MathJax || !MathJax.typesetPromise || mathJaxPending) return;
  mathJaxPending = true;
  requestAnimationFrame(()=>{
    MathJax.typesetPromise([$("papers")]).catch(()=>{}).finally(()=>{ mathJaxPending = false; });
  });
}
function renderResults(){
  const rows=filtered(), size=Number($("pageSizeFilter").value), pages=Math.max(1,Math.ceil(rows.length/size)); page=Math.min(page,pages);
  $("count").textContent=`${fmt(rows.length)} / ${fmt(PAPERS.length)} papers`;
  const filters=[];
  for(const [label,id] of [["type","typeFilter"],["phylum","phylumFilter"],["class","classFilter"],["country","countryFilter"],["aff","affFilter"]]) {
    if($(id).value) filters.push({label:`${label}: ${$(id).value}`, kind:"select", target:id});
  }
  for(const key of ["author","genus","order"]) {
    if(state[key]) filters.push({label:`${key}: ${state[key]}`, kind:"state", target:key});
  }
  if(state.authorCount) filters.push({label:`authors: ${state.authorCount}`, kind:"state", target:"authorCount"});
  $("activeFilters").innerHTML = filters.map(f=>`<span class="filter-chip" title="Remove filter" data-kind="${f.kind}" data-target="${escapeHtml(f.target)}">${escapeHtml(f.label)}</span>`).join("");
  $("activeFilters").querySelectorAll(".filter-chip").forEach(el=>el.addEventListener("click",()=>clearActiveFilter(el.dataset.kind, el.dataset.target)));
  const slice=rows.slice((page-1)*size,page*size);
  $("papers").innerHTML = slice.map(p=>`<article class="paper"><div class="meta"><span class="badge ${p.type}">${p.type}</span><span>${escapeHtml(p.primary_phylum)}</span><span>${p.author_count} authors</span>${p.paper_url?`<a class="paper-link" href="${escapeHtml(p.paper_url)}" target="_blank" rel="noopener" title="Open arXiv paper" onclick="event.stopPropagation()">Paper</a>`:""}</div><div class="title">${mark(p.title)} <span style="color:var(--muted-2);font-size:11px">click</span></div><div class="authors">${renderAuthors(p)}</div><div class="affs">${renderAffiliations(p)}</div><div class="topics">${p.topics.slice(0,5).map(t=>renderTopicChip(t)).join("")}</div><div class="abstract">${p.abstract?mark(p.abstract):"<span style='color:var(--muted)'>No abstract.</span>"}</div></article>`).join("");
  $("papers").querySelectorAll(".paper .title").forEach(el=>el.addEventListener("click",()=>el.closest(".paper").classList.toggle("open")));
  $("papers").querySelectorAll(".topic-chip").forEach(el=>el.addEventListener("click",()=>setFilter("phylumFilter",el.dataset.phylum)));
  $("papers").querySelectorAll(".author-token").forEach(el=>el.addEventListener("click",(e)=>{e.stopPropagation();setAuthorFilter(el.dataset.author);}));
  $("papers").querySelectorAll(".aff-token").forEach(el=>el.addEventListener("click",(e)=>{e.stopPropagation();setFilter("affFilter",el.dataset.aff);}));
  $("pager").innerHTML = `<button class="btn-clear" ${page<=1?"disabled":""} id="prevPage">Prev</button><span>Page ${page} / ${pages}</span><button class="btn-clear" ${page>=pages?"disabled":""} id="nextPage">Next</button>`;
  $("prevPage").onclick=()=>{page--;renderResults()}; $("nextPage").onclick=()=>{page++;renderResults()};
  typesetVisibleMath();
  replaceUri();
}
function downloadExplorerJson(){
  const payload = {papers:PAPERS, tree:TREE, summary:SUMMARY};
  const blob = new Blob([JSON.stringify(payload, null, 2)], {type:"application/json"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "cvpr2026_explorer_data.json";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(()=>URL.revokeObjectURL(url), 1000);
}
function wire(){
  document.querySelectorAll("aside a").forEach(a=>a.addEventListener("click",()=>{document.querySelectorAll("aside a").forEach(x=>x.classList.remove("active"));a.classList.add("active")}));
  ["q","q2","q3"].forEach(id=>$(id).addEventListener("input",()=>{page=1;renderResults()}));
  ["searchMode","typeFilter","phylumFilter","classFilter","countryFilter","affFilter","sortFilter","pageSizeFilter"].forEach(id=>$(id).addEventListener("change",()=>{page=1;state.genus="";renderResults()}));
  $("clearFilters").onclick=()=>{clearFilterState();renderResults();replaceUri("#search");};
  $("downloadJson").onclick=downloadExplorerJson;
  $("brandHome").onclick=()=>{$("clearFilters").click();};
  window.addEventListener("popstate",()=>{urlSyncReady=false;applyUriState();urlSyncReady=true;renderResults();});
}
populateFilters(); applyUriState(); renderTree(); renderHeatmap(); render3DPhylumBars(); wire(); urlSyncReady=true; renderResults();
$("genDate").textContent = new Date().toISOString().slice(0,10);
</script>
</body>
</html>
"""


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_html(), encoding="utf-8", newline="\n")
    METHOD_OUT.write_text(build_methodology_html(), encoding="utf-8", newline="\n")
    AFF_RANKINGS_OUT.write_text(build_affiliation_rankings_md(), encoding="utf-8", newline="\n")
    AFF_RANKINGS_HTML_OUT.write_text(build_affiliation_rankings_html(), encoding="utf-8", newline="\n")
    OTHER_AFFILIATIONS_OUT.write_text(build_other_affiliations_md(), encoding="utf-8", newline="\n")
    OTHER_AFFILIATIONS_HTML_OUT.write_text(build_other_affiliations_html(), encoding="utf-8", newline="\n")
    print(OUT)
    print(METHOD_OUT)
    print(AFF_RANKINGS_OUT)
    print(AFF_RANKINGS_HTML_OUT)
    print(OTHER_AFFILIATIONS_OUT)
    print(OTHER_AFFILIATIONS_HTML_OUT)


if __name__ == "__main__":
    main()
