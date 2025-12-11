"""
非同期処理への移行サンプルコード
現在の同期実装と非同期実装の比較例
"""

import asyncio
import time
from typing import List, Dict, Optional
import json

# ============================================================================
# 例1: OpenAI API呼び出しの非同期化
# ============================================================================

# === 現在の実装（同期） ===
def current_sync_recommendation(user_text: str) -> Dict:
    """現在の同期的な推奨処理（順次実行）"""
    from openai import OpenAI
    
    client = OpenAI(api_key="your-api-key")
    
    # ステップ1: 症状抽出（2〜5秒）
    start_time = time.time()
    symptoms_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"Extract symptoms from: {user_text}"}]
    )
    symptoms = symptoms_response.choices[0].message.content
    step1_time = time.time() - start_time
    
    # ステップ2: 属性抽出（2〜5秒）
    start_time = time.time()
    attributes_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"Extract user attributes from: {user_text}"}]
    )
    attributes = attributes_response.choices[0].message.content
    step2_time = time.time() - start_time
    
    # ステップ3: 推奨生成（2〜5秒）
    start_time = time.time()
    recommendation_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"Recommend medicine for: {symptoms}"}]
    )
    recommendation = recommendation_response.choices[0].message.content
    step3_time = time.time() - start_time
    
    total_time = step1_time + step2_time + step3_time
    print(f"⏱️ 同期処理合計時間: {total_time:.2f}秒")
    print(f"  - 症状抽出: {step1_time:.2f}秒")
    print(f"  - 属性抽出: {step2_time:.2f}秒")
    print(f"  - 推奨生成: {step3_time:.2f}秒")
    
    return {
        "symptoms": symptoms,
        "attributes": attributes,
        "recommendation": recommendation
    }


# === 非同期実装（並列実行） ===
async def async_recommendation(user_text: str) -> Dict:
    """非同期的な推奨処理（並列実行）"""
    from openai import AsyncOpenAI
    
    client = AsyncOpenAI(api_key="your-api-key")
    
    start_time = time.time()
    
    # ステップ1と2を並列実行（最大50% 高速化）
    symptoms_task = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"Extract symptoms from: {user_text}"}]
    )
    
    attributes_task = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"Extract user attributes from: {user_text}"}]
    )
    
    # 並列実行を待つ
    symptoms_response, attributes_response = await asyncio.gather(
        symptoms_task,
        attributes_task
    )
    
    symptoms = symptoms_response.choices[0].message.content
    attributes = attributes_response.choices[0].message.content
    parallel_time = time.time() - start_time
    
    # ステップ3: 推奨生成
    start_time = time.time()
    recommendation_response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"Recommend medicine for: {symptoms}"}]
    )
    recommendation = recommendation_response.choices[0].message.content
    recommendation_time = time.time() - start_time
    
    total_time = parallel_time + recommendation_time
    print(f"⚡ 非同期処理合計時間: {total_time:.2f}秒")
    print(f"  - 症状抽出 + 属性抽出（並列）: {parallel_time:.2f}秒")
    print(f"  - 推奨生成: {recommendation_time:.2f}秒")
    print(f"  - 改善率: {((6 - total_time) / 6 * 100):.1f}% 高速化")
    
    return {
        "symptoms": symptoms,
        "attributes": attributes,
        "recommendation": recommendation
    }


# ============================================================================
# 例2: データベースアクセスの非同期化
# ============================================================================

# === 現在の実装（psycopg2同期） ===
def current_sync_db_operations():
    """現在の同期的なDB操作"""
    import psycopg2
    from psycopg2 import pool
    
    # 接続プール作成
    connection_pool = pool.ThreadedConnectionPool(
        minconn=2,
        maxconn=10,
        host="localhost",
        database="medicine_db",
        user="postgres",
        password="password"
    )
    
    start_time = time.time()
    
    # 100件のセッションを順次読み込み
    sessions = []
    for i in range(100):
        conn = connection_pool.getconn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = %s", (i,))
        session = cursor.fetchone()
        sessions.append(session)
        cursor.close()
        connection_pool.putconn(conn)
    
    total_time = time.time() - start_time
    print(f"⏱️ 同期DB操作: {total_time:.2f}秒 (100件)")
    
    return sessions


# === 非同期実装（asyncpg） ===
async def async_db_operations():
    """非同期的なDB操作"""
    import asyncpg
    
    # 接続プール作成
    pool = await asyncpg.create_pool(
        host="localhost",
        database="medicine_db",
        user="postgres",
        password="password",
        min_size=2,
        max_size=10
    )
    
    start_time = time.time()
    
    # 100件のセッションを並列読み込み
    async def fetch_session(session_id: int):
        async with pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM sessions WHERE id = $1", session_id)
    
    # 10件ずつ並列実行（同時接続数を制限）
    sessions = []
    for i in range(0, 100, 10):
        batch = await asyncio.gather(
            *[fetch_session(j) for j in range(i, min(i + 10, 100))]
        )
        sessions.extend(batch)
    
    total_time = time.time() - start_time
    print(f"⚡ 非同期DB操作: {total_time:.2f}秒 (100件)")
    print(f"  - 改善率: {((2.0 - total_time) / 2.0 * 100):.1f}% 高速化")
    
    await pool.close()
    return sessions


# ============================================================================
# 例3: FastAPIエンドポイント実装
# ============================================================================

# === 現在の実装（Flask同期） ===
"""
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/recommend', methods=['POST'])
def recommend():
    data = request.json
    user_text = data.get('message')
    
    # 同期処理（4〜15秒）
    result = current_sync_recommendation(user_text)
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
"""


# === 非同期実装（FastAPI） ===
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Medicine Recommendation API")

class RecommendRequest(BaseModel):
    message: str
    user_info: Optional[Dict] = {}

class RecommendResponse(BaseModel):
    symptoms: str
    attributes: str
    recommendation: str
    processing_time: float

@app.post('/api/recommend', response_model=RecommendResponse)
async def recommend(request: RecommendRequest):
    '''非同期推奨エンドポイント'''
    try:
        start_time = time.time()
        
        # 非同期処理（2〜8秒）
        result = await async_recommendation(request.message)
        
        processing_time = time.time() - start_time
        
        return RecommendResponse(
            symptoms=result['symptoms'],
            attributes=result['attributes'],
            recommendation=result['recommendation'],
            processing_time=processing_time
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000, workers=4)
"""


# ============================================================================
# 例4: セッション管理の非同期化（Redis）
# ============================================================================

# === 現在の実装（PostgreSQL同期） ===
class CurrentSyncSessionManager:
    """現在の同期的なセッション管理"""
    
    def __init__(self):
        import psycopg2
        self.conn = psycopg2.connect(
            host="localhost",
            database="medicine_db",
            user="postgres",
            password="password"
        )
    
    def save_session(self, session_id: str, data: Dict) -> bool:
        """セッション保存（30〜50ms）"""
        start_time = time.time()
        
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO sessions (session_id, data, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (session_id) DO UPDATE SET
                data = EXCLUDED.data,
                updated_at = NOW()
            """,
            (session_id, json.dumps(data))
        )
        self.conn.commit()
        cursor.close()
        
        elapsed = (time.time() - start_time) * 1000
        print(f"⏱️ 同期セッション保存: {elapsed:.2f}ms")
        return True
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """セッション取得（20〜40ms）"""
        start_time = time.time()
        
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT data FROM sessions WHERE session_id = %s",
            (session_id,)
        )
        result = cursor.fetchone()
        cursor.close()
        
        elapsed = (time.time() - start_time) * 1000
        print(f"⏱️ 同期セッション取得: {elapsed:.2f}ms")
        
        if result:
            return json.loads(result[0])
        return None


# === 非同期実装（Redis） ===
class AsyncSessionManager:
    """非同期的なセッション管理（Redis使用）"""
    
    def __init__(self):
        self.redis_url = "redis://localhost:6379"
        self.redis = None
    
    async def connect(self):
        """Redis接続"""
        import aioredis
        self.redis = await aioredis.create_redis_pool(self.redis_url)
    
    async def save_session(self, session_id: str, data: Dict, ttl: int = 3600) -> bool:
        """セッション保存（1〜5ms）- 10倍以上高速"""
        start_time = time.time()
        
        await self.redis.setex(
            f"session:{session_id}",
            ttl,
            json.dumps(data, ensure_ascii=False)
        )
        
        elapsed = (time.time() - start_time) * 1000
        print(f"⚡ 非同期セッション保存: {elapsed:.2f}ms")
        print(f"  - 改善率: PostgreSQLより {30 / elapsed:.1f}倍高速")
        return True
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """セッション取得（0.5〜2ms）- 20倍以上高速"""
        start_time = time.time()
        
        data = await self.redis.get(f"session:{session_id}")
        
        elapsed = (time.time() - start_time) * 1000
        print(f"⚡ 非同期セッション取得: {elapsed:.2f}ms")
        print(f"  - 改善率: PostgreSQLより {20 / elapsed:.1f}倍高速")
        
        if data:
            return json.loads(data)
        return None
    
    async def close(self):
        """Redis接続を閉じる"""
        if self.redis:
            self.redis.close()
            await self.redis.wait_closed()


# ============================================================================
# 例5: 複数タスクの並列実行（高度な例）
# ============================================================================

async def advanced_parallel_processing(user_text: str, session_id: str) -> Dict:
    """
    複数の非同期タスクを効率的に並列実行
    
    並列実行により、合計時間を大幅に短縮：
    - 同期処理: 6〜15秒
    - 非同期処理: 2〜5秒（60〜70% 高速化）
    """
    from openai import AsyncOpenAI
    
    client = AsyncOpenAI(api_key="your-api-key")
    session_manager = AsyncSessionManager()
    await session_manager.connect()
    
    start_time = time.time()
    
    # タスク1: セッション取得
    session_task = session_manager.get_session(session_id)
    
    # タスク2: 症状抽出
    symptoms_task = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"Extract symptoms: {user_text}"}]
    )
    
    # タスク3: 属性抽出
    attributes_task = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"Extract attributes: {user_text}"}]
    )
    
    # 全タスクを並列実行
    session_data, symptoms_response, attributes_response = await asyncio.gather(
        session_task,
        symptoms_task,
        attributes_task
    )
    
    parallel_time = time.time() - start_time
    print(f"⚡ 並列実行時間: {parallel_time:.2f}秒")
    
    # 結果を使って推奨生成
    symptoms = symptoms_response.choices[0].message.content
    attributes = attributes_response.choices[0].message.content
    
    recommendation_response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"Recommend: {symptoms}"}]
    )
    recommendation = recommendation_response.choices[0].message.content
    
    # 結果を保存（非同期）
    result_data = {
        "symptoms": symptoms,
        "attributes": attributes,
        "recommendation": recommendation,
        "timestamp": time.time()
    }
    
    await session_manager.save_session(session_id, result_data)
    await session_manager.close()
    
    total_time = time.time() - start_time
    print(f"⚡ 合計処理時間: {total_time:.2f}秒")
    print(f"  - 改善率: 同期処理より {((10 - total_time) / 10 * 100):.1f}% 高速化")
    
    return result_data


# ============================================================================
# 例6: エラーハンドリングとタイムアウト
# ============================================================================

async def async_with_error_handling(user_text: str) -> Dict:
    """
    適切なエラーハンドリングとタイムアウト設定
    """
    from openai import AsyncOpenAI
    import asyncio
    
    client = AsyncOpenAI(api_key="your-api-key")
    
    try:
        # タイムアウト付きで実行（5秒）
        async with asyncio.timeout(5.0):
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": user_text}]
            )
            return {"status": "success", "content": response.choices[0].message.content}
    
    except asyncio.TimeoutError:
        print("⚠️ タイムアウトエラー: 5秒以内に完了しませんでした")
        return {"status": "error", "message": "Request timeout"}
    
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        return {"status": "error", "message": str(e)}


# ============================================================================
# 例7: 負荷テスト（同期 vs 非同期）
# ============================================================================

def load_test_sync(num_requests: int = 10):
    """同期処理の負荷テスト"""
    print(f"\n🔄 同期処理 - {num_requests}リクエスト")
    start_time = time.time()
    
    for i in range(num_requests):
        # 各リクエストが順次実行される
        result = simulate_sync_request(i)
    
    total_time = time.time() - start_time
    avg_time = total_time / num_requests
    
    print(f"⏱️ 合計時間: {total_time:.2f}秒")
    print(f"⏱️ 平均時間: {avg_time:.2f}秒/request")
    print(f"⏱️ スループット: {num_requests / total_time:.2f} req/sec")


async def load_test_async(num_requests: int = 10, concurrency: int = 5):
    """非同期処理の負荷テスト"""
    print(f"\n⚡ 非同期処理 - {num_requests}リクエスト（並列度: {concurrency}）")
    start_time = time.time()
    
    # セマフォで並列度を制限
    semaphore = asyncio.Semaphore(concurrency)
    
    async def limited_request(i):
        async with semaphore:
            return await simulate_async_request(i)
    
    # 全リクエストを並列実行
    results = await asyncio.gather(
        *[limited_request(i) for i in range(num_requests)]
    )
    
    total_time = time.time() - start_time
    avg_time = total_time / num_requests
    
    print(f"⚡ 合計時間: {total_time:.2f}秒")
    print(f"⚡ 平均時間: {avg_time:.2f}秒/request")
    print(f"⚡ スループット: {num_requests / total_time:.2f} req/sec")
    
    improvement = ((load_test_sync.__defaults__[0] / (num_requests / total_time)) - 1) * 100
    print(f"⚡ 改善率: {improvement:.1f}% 高速化")


# シミュレーション関数
def simulate_sync_request(request_id: int) -> Dict:
    """同期リクエストのシミュレーション（500ms）"""
    time.sleep(0.5)
    return {"id": request_id, "status": "completed"}


async def simulate_async_request(request_id: int) -> Dict:
    """非同期リクエストのシミュレーション（500ms）"""
    await asyncio.sleep(0.5)
    return {"id": request_id, "status": "completed"}


# ============================================================================
# メイン実行
# ============================================================================

async def main():
    """サンプルコードの実行"""
    
    print("=" * 70)
    print("🚀 非同期処理への移行サンプルコード実行")
    print("=" * 70)
    
    # 例1: API呼び出しの比較
    print("\n📌 例1: OpenAI API呼び出しの比較")
    print("-" * 70)
    # user_text = "頭痛と発熱があります"
    # result = await async_recommendation(user_text)
    
    # 例2: DB操作の比較
    print("\n📌 例2: データベース操作の比較")
    print("-" * 70)
    # sessions = await async_db_operations()
    
    # 例3: セッション管理の比較
    print("\n📌 例3: セッション管理の比較")
    print("-" * 70)
    session_manager = AsyncSessionManager()
    await session_manager.connect()
    
    test_data = {"user": "test", "messages": []}
    await session_manager.save_session("test-session-123", test_data)
    retrieved = await session_manager.get_session("test-session-123")
    print(f"取得したセッション: {retrieved}")
    
    await session_manager.close()
    
    # 例4: 負荷テスト
    print("\n📌 例4: 負荷テスト（同期 vs 非同期）")
    print("-" * 70)
    load_test_sync(10)
    await load_test_async(10, concurrency=5)
    
    print("\n" + "=" * 70)
    print("✅ サンプルコード実行完了")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

