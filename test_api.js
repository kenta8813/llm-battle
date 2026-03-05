/**
 * API統合テスト
 */

const API_BASE = 'http://localhost:3000/api';

async function testAPI() {
    console.log('='.repeat(60));
    console.log('API統合テスト開始');
    console.log('='.repeat(60));

    let token = null;
    let accountId = null;
    let characterId = null;

    try {
        // 1. アカウント作成
        console.log('\n[1/6] アカウント作成...');
        const accountRes = await fetch(`${API_BASE}/accounts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: `testuser_${Date.now()}` })
        });
        const accountData = await accountRes.json();
        console.log('✓ アカウント作成成功:', accountData);
        token = accountData.token;
        accountId = accountData.account_id;

        // 2. アビリティ一覧取得
        console.log('\n[2/6] アビリティ一覧取得...');
        const abilitiesRes = await fetch(`${API_BASE}/characters/abilities`);
        const abilitiesData = await abilitiesRes.json();
        console.log('レスポンス:', abilitiesData);
        if (!abilitiesData.abilities) {
            throw new Error('abilities プロパティが見つかりません');
        }
        console.log(`✓ アビリティ一覧取得成功: ${abilitiesData.abilities.length}個`);
        console.log('利用可能なアビリティ:');
        abilitiesData.abilities.forEach(a => {
            console.log(`  - [${a.id}] ${a.name}: ${a.description}`);
        });

        // 3. キャラクター作成
        console.log('\n[3/6] キャラクター作成...');
        const charRes = await fetch(`${API_BASE}/characters`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                account_id: accountId,
                name: 'テストキャラ',
                prompt: '素早い動きで敵を翻弄する剣士。攻撃力と速度に優れるが、防御は脆い。',
                base_hp: 60,
                base_attack: 80,
                base_defense: 40,
                base_speed: 100,
                ability_ids: [1, 2]
            })
        });
        const charData = await charRes.json();
        console.log('✓ キャラクター作成成功:', charData);
        characterId = charData.character_id;

        // 4. キャラクター情報取得
        console.log('\n[4/6] キャラクター情報取得...');
        const charInfoRes = await fetch(`${API_BASE}/characters/${characterId}`);
        const charInfo = await charInfoRes.json();
        console.log('✓ キャラクター情報取得成功:', charInfo.character);

        // 5. マッチングキュー参加
        console.log('\n[5/6] マッチングキュー参加...');
        const queueRes = await fetch(`${API_BASE}/queue`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ character_id: characterId })
        });
        const queueData = await queueRes.json();
        console.log('✓ キュー参加成功:', queueData);

        // 6. キュー離脱
        console.log('\n[6/6] マッチングキュー離脱...');
        const leaveRes = await fetch(`${API_BASE}/queue/${characterId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const leaveData = await leaveRes.json();
        console.log('✓ キュー離脱成功:', leaveData);

        console.log('\n' + '='.repeat(60));
        console.log('✓ すべてのテスト成功！');
        console.log('='.repeat(60));

    } catch (error) {
        console.error('\n❌ テスト失敗:', error.message);
        console.error(error);
        process.exit(1);
    }
}

testAPI();
