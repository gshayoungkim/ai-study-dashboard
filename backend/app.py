from flask import Flask, render_template, jsonify, request
from github import Github, GithubException
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
import re
import time
from supabase import create_client, Client

# 로컬 개발 환경 지원
if os.path.exists('.env'):
    load_dotenv()

app = Flask(__name__)

# GitHub 토큰 설정
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN') or os.getenv('GITHUB_TOKEN_BACKUP')

print(f"\n{'='*60}")
print("[INIT] GitHub 토큰 확인")
print(f"  토큰: {GITHUB_TOKEN[:20] if GITHUB_TOKEN else 'None'}...")

if GITHUB_TOKEN:
    try:
        g = Github(GITHUB_TOKEN)
        g.get_user().login
        print(f"  ✓ GitHub 연결 성공")
    except Exception as e:
        print(f"  ✗ GitHub 연결 실패: {str(e)}")
        g = None
else:
    g = None
    print(f"  [WARNING] GitHub API 사용 불가")
print(f"{'='*60}\n")

# Supabase 설정
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print(f"\n{'='*60}")
    print("[INIT] Supabase 연결 확인")
    print(f"  URL: {SUPABASE_URL[:30]}...")
    print(f"{'='*60}\n")
else:
    supabase = None
    print("[WARNING] Supabase 환경 변수 없음")

QUIZ_DATA_FILE = 'quiz_results.json'

cache = {
    'submissions': None,
    'last_updated': 0,
    'cache_duration': 300
}

# QUIZZES 데이터
QUIZZES = {
    "ch01": [
        {
            "id": "ch01",
            "title": "Ch01-1 - 머신러닝 개요",
            "gemini_link": "https://gemini.google.com/share/cd026cf98350"
        },
    ],
    "ch02": [
        {
            "id": "ch02-1",
            "title": "Ch02-1 - 훈련 세트와 테스트 세트 퀴즈",
            "gemini_link": "https://gemini.google.com/share/f1f3d7a544e3"
        },
        {
            "id": "ch02-2",
            "title": "Ch02-2 - 데이터 전처리",
            "gemini_link": "https://gemini.google.com/share/d13ebaf4c393"
        }
    ],
    "ch03": [
        {
            "id": "ch03",
            "title": "Ch03 - 회귀알고리즘과 모델 규제",
            "gemini_link": "https://gemini.google.com/share/f9fa458276d3"
        }
    ],
    "ch04": [
        {
            "id": "ch04-1",
            "title": "Ch04 - 다양한 알고리즘(1)",
            "gemini_link": "https://gemini.google.com/share/4ea0e7137b74"
        },
        {
            "id": "ch04-2",
            "title": "Ch04 - 다양한 알고리즘(2)",
            "gemini_link": "https://gemini.google.com/share/770a512a89ef"
        }
    ],
    "ch05": [
        {
            "id": "ch05-1",
            "title": "Ch05-1 - 결정트리",
            "gemini_link": "https://gemini.google.com/share/58b3bbcd177d"
        },
        {
            "id": "ch05-2",
            "title": "Ch05-2 - 교차검증과 그리드서치",
            "gemini_link": "https://gemini.google.com/share/5fe85dc6304d"
        },
        {
            "id": "ch05-3",
            "title": "Ch05-3 - 트리의 앙상블",
            "gemini_link": "https://gemini.google.com/share/5e9c9c72468f"
        }
    ],
    "ch06": [
        {
            "id": "ch06-1",
            "title": "Ch06-1 - 군집 알고리즘",
            "gemini_link": "https://gemini.google.com/share/6e89a727743c"
        },
        {
            "id": "ch06-2",
            "title": "Ch06-2 - k-평균",
            "gemini_link": "https://gemini.google.com/share/0345af73e04c"
        },
        {
            "id": "ch06-3",
            "title": "Ch06-3 - 주성분 분석 퀴즈",
            "gemini_link": "https://gemini.google.com/share/be17f7e135ad"
        }
    ],
        "ch07": [
        {
            "id": "ch07-1",
            "title": "Ch07-1 - 인공 신경망",
            "gemini_link": "https://gemini.google.com/share/07861a505086"
        },
        {
            "id": "ch07-2",
            "title": "Ch0-2 - 심층 신경망",
            "gemini_link": "https://gemini.google.com/share/690bd417b27e"
        },
        {
            "id": "ch07-3",
            "title": "Ch07-3 - 신경망 모델 훈련",
            "gemini_link": "https://gemini.google.com/share/006b17105893"
        }
    ]
}

# 레포지토리 매핑
REPO_NAME_MAPPING = {
    "hayoung-kim": "김하영",
    "minjeong-ko": "고민정",
    "hagyeong-lee": "이하경",
    "yeonseok-kim": "김연석",
    "eunyong-choi": "최은용",
    "sujeung-kim": "김수정",
    "yunjae-gim": "김윤재",
    "seongyeong-kim": "김선경",
    "soyeon-park": "박소연",
    "zeho-oh": "오제호",
    "yeji-kim": "김예지",
    "jihoon-jung": "정지훈",
    "sieun-lee": "이시은",
    "suhyeon-min": "민수현",
    "sungkyeong-bae": "배성경",
    "jiwoo-yoon": "윤지우",
    "bonwook-gu": "구본욱",
    "sungmin-hwang": "황성민",
    "soyeon-lee": "이소연",
    "sooneun-bae": "배순은",
    "dayeon-kang": "강다연",
    "haeyin-lee": "이혜인",
    "jooyoung-lee": "이주영",
    "youlim-hong": "홍유림",
    "heejoon-kang": "강희준",
    "chanho-ma": "마찬호",
    "juyoung-noh": "노주영",
    "sulim-lee": "이수림",
    "yoonjung-koo": "구윤정",
    "serim-lee": "이세림",
    "hyoeun-ji" : "지효은",
    "seonmin-lee" : "이선민",
    "heeseung-han" : "한희승",


}

PART1_MEMBERS = [
    "hayoung-kim",
    "minjeong-ko", 
    "hagyeong-lee",
    "yeonseok-kim",
    "eunyong-choi",
    "sujeung-kim",
    "yunjae-gim",
    "seongyeong-kim",
    "soyeon-park",
    "zeho-oh",
    "jihoon-jung",
    "sieun-lee",
    "suhyeon-min",
    "sungkyeong-bae",
]

PART2_MEMBERS = [
    "yeji-kim",
    "jiwoo-yoon",
    "bonwook-gu",
    "sungmin-hwang",
    "soyeon-lee",
    "sooneun-bae",
    "dayeon-kang",
    "haeyin-lee",
    "jooyoung-lee",
    "youlim-hong",
    "heejoon-kang",
    "chanho-ma",
    "juyoung-noh",
    "sulim-lee",
    "yoonjung-koo",
    "serim-lee",
    "hyoeun-ji",
    "seonmin-lee",
    "heeseung-han"

]

STUDY_CONFIG = {
    "org_name": "oracleaistudy",
    "book_name": "혼자 공부하는 머신러닝 딥러닝",
    "part1_current_chapter": "7",
    "part2_current_chapter": "1-2",
     "org_name": "oracleaistudy",
    
}


def fetch_all_submissions():
    if not g:
        print("[ERROR] GitHub 연결 불가능 (토큰 없음)")
        return {}

    current_time = time.time()
    
    # 캐시 유효기간 내라면 캐시 반환
    if cache['submissions'] is not None and (current_time - cache['last_updated']) < cache['cache_duration']:
        return cache['submissions']
    
    submission_matrix = {}

    for repo_name, person_name in REPO_NAME_MAPPING.items():
        submission_matrix[repo_name] = {
            'name': person_name,
            'submissions': {},
            'total_completed': 0,
            'chapters': {},
        }
        for i in range(1, 11):
            ch_key = f'ch{i:02d}'
            submission_matrix[repo_name]['submissions'][ch_key] = {
                'completed': False,
                'url': None,
                'filename': None
            }
            submission_matrix[repo_name]['chapters'][ch_key] = False

    try:
        org = g.get_organization(STUDY_CONFIG['org_name'])
        repos = list(org.get_repos())

        for repo in repos:
            repo_name = repo.name

            if repo_name in REPO_NAME_MAPPING:
                try:
                    contents = repo.get_contents("")
                    files = [f for f in contents if not isinstance(f, dict)]
                    ipynb_files = [f for f in files if f.name.endswith('.ipynb')]

                    for file in ipynb_files:
                        detected_chapter = detect_chapter_from_filename(file.name)

                        if detected_chapter:
                            ch_key = detected_chapter
                            if not submission_matrix[repo_name]['submissions'][ch_key]['completed']:
                                submission_matrix[repo_name]['submissions'][ch_key] = {
                                    'completed': True,
                                    'url': file.html_url,
                                    'filename': file.name
                                }
                                submission_matrix[repo_name]['chapters'][ch_key] = True
                                submission_matrix[repo_name]['total_completed'] += 1

                except GithubException as e:
                    print(f"[ERROR] {repo_name}: {e.status}")
                except Exception as e:
                    print(f"[ERROR] {repo_name}: {str(e)}")

    except Exception as e:
        print(f"[ERROR] 조직 접근 실패: {str(e)}")

    cache['submissions'] = submission_matrix
    cache['last_updated'] = current_time

    return submission_matrix
    
def detect_chapter_from_filename(filename):
    """파일명에서 챕터 번호를 감지"""
    filename_lower = filename.lower()
    filename_clean = ''.join(
        c for c in filename_lower 
        if not ('\uac00' <= c <= '\ud7a3')
    )
    
    patterns = [
        (r'ch[_\-\s]?(\d{2})', '형식: ch01'),
        (r'chapter[_\-\s]?(\d{2})', '형식: chapter01'),
        (r'ch[_\-\s]?([1-9])(?![0-9])', '형식: ch1'),
        (r'chapter[_\-\s]?([1-9])(?![0-9])', '형식: chapter1'),
        (r'chap[_\-\s]?(\d{2})', '형식: chap01'),
        (r'chap[_\-\s]?([1-9])(?![0-9])', '형식: chap1'),
        (r'week[_\-\s]?(\d{2})', '형식: week01'),
        (r'week[_\-\s]?([1-9])(?![0-9])', '형식: week1'),
        (r'^(\d{1,2})[_\-\s]', '형식: 01-'),
        (r'^(\d{1,2})\.', '형식: 01.'),
    ]
    
    for pattern, pattern_desc in patterns:
        match = re.search(pattern, filename_clean)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 10:
                return f'ch{num:02d}'
    
    return None

# =========================
# 라우트 정의
# =========================

@app.route('/')
def index():
    """간소화된 메인 대시보드"""
    submissions = fetch_all_submissions()
    members_count = len(REPO_NAME_MAPPING)
    
    # PART별 분리
    part1_submissions = {k: v for k, v in submissions.items() if k in PART1_MEMBERS}
    part2_submissions = {k: v for k, v in submissions.items() if k in PART2_MEMBERS}
    
    # 현재 진행 챕터 (범위 지원)
    part1_current_str = STUDY_CONFIG.get('part1_current_chapter', '6')
    part2_current_str = STUDY_CONFIG.get('part2_current_chapter', '2')
    
    # 챕터 범위를 리스트로 변환하는 함수
    def parse_chapter_range(chapter_str):
        """
        '1-2' -> [1, 2]
        '6' -> [6]
        '3-4' -> [3, 4]
        """
        try:
            if '-' in chapter_str:
                start, end = chapter_str.split('-')
                return list(range(int(start), int(end) + 1))
            else:
                return [int(chapter_str)]
        except:
            return [1]
    
    part1_chapters = parse_chapter_range(part1_current_str)
    part2_chapters = parse_chapter_range(part2_current_str)
    
    # 마지막 챕터 번호 (제출률 계산용)
    part1_current_ch = max(part1_chapters)
    part2_current_ch = max(part2_chapters)
    
    # PART1 과제 제출 상태 (범위 내 모든 챕터 완료 여부)
    part1_submitted = 0
    for repo_name in PART1_MEMBERS:
        if repo_name in submissions:
            # 해당 범위의 모든 챕터를 완료했는지 확인
            all_completed = True
            for ch_num in part1_chapters:
                ch_key = f'ch{ch_num:02d}'
                if not submissions[repo_name]['submissions'][ch_key]['completed']:
                    all_completed = False
                    break
            
            if all_completed:
                part1_submitted += 1
    
    part1_submit_rate = round((part1_submitted / len(PART1_MEMBERS)) * 100) if PART1_MEMBERS else 0
    part1_not_submit_rate = 100 - part1_submit_rate
    
    # PART2 과제 제출 상태 (범위 내 모든 챕터 완료 여부)
    part2_submitted = 0
    for repo_name in PART2_MEMBERS:
        if repo_name in submissions:
            # 해당 범위의 모든 챕터를 완료했는지 확인
            all_completed = True
            for ch_num in part2_chapters:
                ch_key = f'ch{ch_num:02d}'
                if not submissions[repo_name]['submissions'][ch_key]['completed']:
                    all_completed = False
                    break
            
            if all_completed:
                part2_submitted += 1
    
    part2_submit_rate = round((part2_submitted / len(PART2_MEMBERS)) * 100) if PART2_MEMBERS else 0
    part2_not_submit_rate = 100 - part2_submit_rate
    
    # 전체 진행률 계산
    total_completed = sum(data['total_completed'] for data in submissions.values())
    total_possible = members_count * 10
    avg_progress = round((total_completed / total_possible) * 100) if total_possible > 0 else 0
    
    # PART별 TOP 3 완료자
    part1_top_users = sorted(
        part1_submissions.items(),
        key=lambda x: x[1]['total_completed'],
        reverse=True
    )[:3]
    
    part2_top_users = sorted(
        part2_submissions.items(),
        key=lambda x: x[1]['total_completed'],
        reverse=True
    )[:3]
    
    # PART별 평균 진행률
    part1_completed = sum(
        submissions[k]['total_completed'] 
        for k in PART1_MEMBERS if k in submissions
    )
    part1_avg = round((part1_completed / (len(PART1_MEMBERS) * 10)) * 100) if PART1_MEMBERS else 0
    
    part2_completed = sum(
        submissions[k]['total_completed'] 
        for k in PART2_MEMBERS if k in submissions
    )
    part2_avg = round((part2_completed / (len(PART2_MEMBERS) * 10)) * 100) if PART2_MEMBERS else 0
    
    # 챕터별 완료 현황 (차트용)
    chapter_stats = {}
    for i in range(1, 11):
        ch_key = f'ch{i:02d}'
        completed_count = sum(
            1 for data in submissions.values()
            if data['submissions'][ch_key]['completed']
        )
        chapter_stats[f'Ch{i:02d}'] = completed_count
    
    # PART별 퀴즈 TOP 3
    part1_quiz_top = []
    part2_quiz_top = []
    
    if supabase:
        try:
            response = supabase.table('quiz_completions').select('*').execute()
            user_counts = {}
            for record in response.data:
                user_name = record['user_name']
                user_counts[user_name] = user_counts.get(user_name, 0) + 1
            
            # PART1 멤버의 이름 목록 생성
            part1_names = [REPO_NAME_MAPPING[repo] for repo in PART1_MEMBERS if repo in REPO_NAME_MAPPING]
            part2_names = [REPO_NAME_MAPPING[repo] for repo in PART2_MEMBERS if repo in REPO_NAME_MAPPING]
            
            # PART별로 분리
            part1_counts = {name: count for name, count in user_counts.items() if name in part1_names}
            part2_counts = {name: count for name, count in user_counts.items() if name in part2_names}
            
            part1_quiz_top = sorted(part1_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            part2_quiz_top = sorted(part2_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        except:
            pass
    
    # 최근 논문 3개
    recent_papers = []
    if supabase:
        try:
            response = supabase.table('papers').select('*').order('created_at', desc=True).limit(3).execute()
            recent_papers = response.data
        except:
            pass
    

    
    return render_template('index.html',
                         members_count=members_count,
                         avg_progress=avg_progress,
                         part1_top_users=part1_top_users,
                         part2_top_users=part2_top_users,
                         part1_avg=part1_avg,
                         part2_avg=part2_avg,
                         chapter_stats=chapter_stats,
                         part1_submissions=part1_submissions,
                         part2_submissions=part2_submissions,
                         part1_quiz_top=part1_quiz_top,
                         part2_quiz_top=part2_quiz_top,
                         part1_submit_rate=part1_submit_rate,
                         part1_not_submit_rate=part1_not_submit_rate,
                         part2_submit_rate=part2_submit_rate,
                         part2_not_submit_rate=part2_not_submit_rate,
                         part1_current_ch=part1_current_str,
                         part2_current_ch=part2_current_str,
                         recent_papers=recent_papers,
                     )





@app.route('/progress')
def progress():
    """개인별 진도 페이지"""
    submissions = fetch_all_submissions()
    
    part1_submissions = {k: v for k, v in submissions.items() if k in PART1_MEMBERS}
    part2_submissions = {k: v for k, v in submissions.items() if k in PART2_MEMBERS}
    
    part1_sorted = dict(sorted(part1_submissions.items(), key=lambda x: x[1]['name']))
    part2_sorted = dict(sorted(part2_submissions.items(), key=lambda x: x[1]['name']))
    
    part1_chapter_stats = {}
    part2_chapter_stats = {}
    
    for i in range(1, 11):
        ch_key = f'ch{i:02d}'
        
        part1_count = sum(
            1 for k, data in part1_submissions.items()
            if data['submissions'][ch_key]['completed']
        )
        part1_chapter_stats[f'Ch{i:02d}'] = part1_count
        
        part2_count = sum(
            1 for k, data in part2_submissions.items()
            if data['submissions'][ch_key]['completed']
        )
        part2_chapter_stats[f'Ch{i:02d}'] = part2_count
    
    return render_template('progress.html',
                         part1_submissions=part1_sorted,
                         part2_submissions=part2_sorted,
                         part1_chapter_stats=part1_chapter_stats,
                         part2_chapter_stats=part2_chapter_stats)

@app.route('/quiz')
def quiz():
    return render_template('quiz.html', quizzes=QUIZZES)

@app.route('/papers')
def papers():
    """논문 게시판 페이지"""
    return render_template('papers.html')

@app.route('/papers/<int:paper_id>')
def paper_detail(paper_id):
    """논문 상세 페이지"""
    return render_template('paper_detail.html', paper_id=paper_id)

@app.route('/api/papers', methods=['GET'])
def get_papers():
    """논문 목록 조회"""
    try:
        if supabase:
            response = supabase.table('papers').select('*').order('created_at', desc=True).execute()
            return jsonify(response.data)
        else:
            return jsonify([]), 500
    except Exception as e:
        print(f"[ERROR] 논문 목록 조회 실패: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/papers/<int:paper_id>', methods=['GET'])
def get_paper(paper_id):
    """논문 상세 조회"""
    try:
        if supabase:
            response = supabase.table('papers').select('*').eq('id', paper_id).execute()
            if response.data:
                return jsonify(response.data[0])
            return jsonify({'error': '논문을 찾을 수 없습니다'}), 404
        else:
            return jsonify({'error': 'Supabase 연결 없음'}), 500
    except Exception as e:
        print(f"[ERROR] 논문 조회 실패: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/papers', methods=['POST'])
def create_paper():
    """논문 등록"""
    try:
        data = request.get_json()
        title = data.get('title')
        author = data.get('author')
        content = data.get('content')
        link = data.get('link')
        
        if not title or not author:
            return jsonify({'error': '제목과 작성자는 필수입니다'}), 400
        
        if supabase:
            response = supabase.table('papers').insert({
                'title': title,
                'author': author,
                'content': content,
                'link': link
            }).execute()
            return jsonify({'success': True, 'data': response.data})
        else:
            return jsonify({'error': 'Supabase 연결 없음'}), 500
            
    except Exception as e:
        print(f"[ERROR] 논문 등록 실패: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/papers/<int:paper_id>/comments', methods=['GET'])
def get_comments(paper_id):
    """댓글 목록 조회"""
    try:
        if supabase:
            response = supabase.table('comments').select('*').eq('paper_id', paper_id).order('created_at', desc=False).execute()
            return jsonify(response.data)
        else:
            return jsonify([]), 500
    except Exception as e:
        print(f"[ERROR] 댓글 조회 실패: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/papers/<int:paper_id>/comments', methods=['POST'])
def create_comment(paper_id):
    """댓글 작성"""
    try:
        data = request.get_json()
        author = data.get('author')
        content = data.get('content')
        
        if not author or not content:
            return jsonify({'error': '작성자와 내용은 필수입니다'}), 400
        
        if supabase:
            response = supabase.table('comments').insert({
                'paper_id': paper_id,
                'author': author,
                'content': content
            }).execute()
            return jsonify({'success': True, 'data': response.data})
        else:
            return jsonify({'error': 'Supabase 연결 없음'}), 500
            
    except Exception as e:
        print(f"[ERROR] 댓글 작성 실패: {str(e)}")
        return jsonify({'error': str(e)}), 500
@app.route('/debug')
def debug():
    submissions = fetch_all_submissions()
    debug_info = []
    
    for repo_name, data in submissions.items():
        user_debug = {
            'name': data['name'],
            'repo_name': repo_name,
            'total': data['total_completed'],
            'files': []
        }
        
        for chapter_key, submission in data['submissions'].items():
            if submission['completed'] and submission.get('filename'):
                user_debug['files'].append({
                    'original_filename': submission['filename'],
                    'detected_chapter': detect_chapter_from_filename(submission['filename']),
                    'chapter_key': chapter_key,
                    'url': submission['url']
                })
        
        debug_info.append(user_debug)
    
    return render_template('debug.html', debug_info=debug_info)

# API 라우트
@app.route('/api/users')
def get_users():
    users = list(REPO_NAME_MAPPING.values())
    return jsonify(sorted(users))

@app.route('/api/quiz-stats')
def quiz_stats():
    try:
        if supabase:
            response = supabase.table('quiz_completions').select('*').execute()
            stats = {}
            
            for chapter, quiz_list in QUIZZES.items():
                for quiz in quiz_list:
                    quiz_id = quiz['id']
                    completed_users = [
                        record['user_name'] 
                        for record in response.data 
                        if record['quiz_id'] == quiz_id
                    ]
                    
                    stats[quiz_id] = {
                        'completed': len(completed_users),
                        'users': completed_users
                    }
            
            return jsonify(stats)
        else:
            quiz_results = load_quiz_results()
            stats = {}
            
            for chapter, quiz_list in QUIZZES.items():
                for quiz in quiz_list:
                    quiz_id = quiz['id']
                    completed_users = [user for user in quiz_results.keys() 
                                      if quiz_id in quiz_results[user].get('completed_quizzes', [])]
                    stats[quiz_id] = {
                        'completed': len(completed_users),
                        'users': completed_users
                    }
            
            return jsonify(stats)
    
    except Exception as e:
        print(f"[ERROR] 퀴즈 통계 조회 실패: {str(e)}")
        return jsonify({}), 500

@app.route('/api/quiz-complete', methods=['POST'])
def quiz_complete():
    try:
        data = request.get_json()
        user_name = data.get('user_name')
        quiz_id = data.get('quiz_id')
        
        if not user_name or not quiz_id:
            return jsonify({'error': '필수 정보 누락'}), 400
        
        if supabase:
            response = supabase.table('quiz_completions').upsert({
                'user_name': user_name,
                'quiz_id': quiz_id,
                'completed_at': datetime.now().isoformat()
            }).execute()
        else:
            quiz_results = load_quiz_results()
            
            if user_name not in quiz_results:
                quiz_results[user_name] = {'completed_quizzes': []}
            
            if quiz_id not in quiz_results[user_name]['completed_quizzes']:
                quiz_results[user_name]['completed_quizzes'].append(quiz_id)
            
            save_quiz_results(quiz_results)
        
        return jsonify({'success': True})
    
    except Exception as e:
        print(f"[ERROR] 퀴즈 완료 기록 실패: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/quiz-leaderboard')
def quiz_leaderboard():
    try:
        if supabase:
            response = supabase.table('quiz_completions').select('*').execute()
            user_counts = {}
            for record in response.data:
                user_name = record['user_name']
                user_counts[user_name] = user_counts.get(user_name, 0) + 1
        else:
            quiz_results = load_quiz_results()
            user_counts = {
                user: len(data.get('completed_quizzes', []))
                for user, data in quiz_results.items()
            }
        
        leaderboard = sorted(
            user_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return jsonify([
            {'rank': idx + 1, 'name': name, 'completed': count}
            for idx, (name, count) in enumerate(leaderboard)
        ])
    
    except Exception as e:
        print(f"[ERROR] 리더보드 조회 실패: {str(e)}")
        return jsonify([]), 500

@app.route('/api/refresh-cache', methods=['POST'])
def refresh_cache():
    cache['submissions'] = None
    cache['last_updated'] = 0
    fetch_all_submissions()
    return jsonify({'success': True, 'message': 'Cache refreshed'})

@app.route('/ranking')
def ranking():
    """종합 랭킹 페이지"""
    submissions = fetch_all_submissions()
    
    # 전체 랭킹 계산
    rankings = []
    for repo_name, data in submissions.items():
        name = data['name']
        chapter_score = data['total_completed'] * 10
        
        # 퀴즈 점수 및 개수
        quiz_count = 0
        quiz_score = 0
        if supabase:
            try:
                response = supabase.table('quiz_completions').select('*').eq('user_name', name).execute()
                quiz_count = len(response.data)
                quiz_score = quiz_count * 5
            except:
                pass
        
        # 논문 점수 및 개수
        paper_count = 0
        paper_score = 0
        if supabase:
            try:
                response = supabase.table('papers').select('*').eq('author', name).execute()
                paper_count = len(response.data)
                paper_score = paper_count * 2
            except:
                pass
        
        total_score = chapter_score + quiz_score + paper_score
        
        
        # 뱃지 계산
        badges = []
        
        # 💎 완벽주의자: 전체 챕터 완료
        if data['total_completed'] >= 10:
            badges.append({'icon': '💎', 'name': '완벽주의자'})
        
        # 🎯 퀴즈 마스터: 퀴즈 10개 이상 완료
        if quiz_count >= 10:
            badges.append({'icon': '🎯', 'name': '퀴즈 마스터'})
        
        # 📚 북웜: 논문 공유 5회 이상
        if paper_count >= 5:
            badges.append({'icon': '📚', 'name': '북웜'})
        
        # 🥇 골드 러너: 6챕터 이상 완료
        if data['total_completed'] >= 6:
            badges.append({'icon': '🥇', 'name': '골드 러너'})
        
        # 🔥 불꽃 학습자: 3챕터 이상 완료
        if data['total_completed'] >= 3:
            badges.append({'icon': '🔥', 'name': '불꽃 학습자'})
        
        
        # 레벨 계산
        if total_score >= 150:
            level = "🏆 그랜드 마스터"
            level_color = "#FFD700"
        elif total_score >= 100:
            level = "💎 마스터"
            level_color = "#C0C0C0"
        elif total_score >= 70:
            level = "⭐ 전문가"
            level_color = "#CD7F32"
        elif total_score >= 40:
            level = "🔥 열정적인 학습자"
            level_color = "#FF6B6B"
        else:
            level = "🌱 초보 학습자"
            level_color = "#51CF66"
        
        rankings.append({
            'name': name,
            'repo_name': repo_name,
            'total_score': total_score,
            'chapter_score': chapter_score,
            'quiz_score': quiz_score,
            'paper_score': paper_score,
            'quiz_count': quiz_count,
            'paper_count': paper_count,
            'badges': badges,
            'level': level,
            'level_color': level_color,
            'chapters_completed': data['total_completed'],
        })
    
    # 점수순 정렬
    rankings.sort(key=lambda x: x['total_score'], reverse=True)
    
    # 순위 부여 (동점 처리)
    current_rank = 0
    prev_score = None
    for idx, data in enumerate(rankings, start=1):
        if data['total_score'] != prev_score:
            current_rank = idx
            prev_score = data['total_score']
        data['rank'] = current_rank
    
    # TOP 3 순위별 그룹 생성
    top_ranks = {}
    for rank_data in rankings:
        rank = rank_data['rank']
        if rank <= 3:
            if rank not in top_ranks:
                top_ranks[rank] = []
            top_ranks[rank].append(rank_data)
    
    return render_template('ranking.html', 
                         rankings=rankings,
                         top_ranks=top_ranks)

if __name__ == '__main__':
    print("\n=== 등록된 라우트 ===")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule.rule}")
    print("=" * 40 + "\n")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)