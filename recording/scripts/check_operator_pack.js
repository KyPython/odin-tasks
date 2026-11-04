'use strict';
const assert = require('node:assert/strict');
const { selectRows, planContent, propertyWrite, PRIMARY } = require('../cloud/operator-pack');
const rt = s => [{ text: { content: s } }];
const row = { id: '3f28621e-0a7a-8141-8d6e-dfb9a5b43054', properties: {
  Task: { title: rt('Cursor') }, Lane: { select: { name: 'Dual-candidate' } }, Stage: { select: { name: 'Candidate' } },
  'Fit Gate': { select: { name: 'PASS' } }, 'Bootcamp Status': { select: { name: 'World building' } },
  'Operator Pack Status': { select: { name: 'PENDING' } }, 'Odin Goal': { rich_text: rt('Exact goal') },
  'Build Issue': { url: 'https://github.com/KyPython/ai-governance/issues/58' }
} };
let checks = 0;
function check(fn) { fn(); checks++; }
check(() => assert.equal(selectRows({ results: [row] }, 'manifest').rows.length, 1));
check(() => assert.equal(selectRows({ results: [row] }, 'pr').rows.length, 0));
check(() => assert.throws(() => selectRows({ results: [row], has_more: true }, 'manifest'), /Incomplete/));
for (const [field, val] of [['Fit Gate', 'HOLD'], ['Stage', 'Rejected'], ['Operator Pack Status', 'READY'], ['Lane', 'Odin monetization']]) {
  check(() => { const r = structuredClone(row); r.properties[field].select.name = val; assert.equal(selectRows({ results: [r] }, 'manifest').count, 0); });
}
const input = { row_id: row.id, blocks: { results: [] }, raw: { verdict: 'PASS', operator_pack: PRIMARY + '\n1. Open the workspace.' },
  source_ref: 'issue 58 comment 123', starter_repository: 'https://github.com/KyPython/example', starter_commit: 'a'.repeat(40) };
let first;
check(() => { first = planContent(input); assert.equal(first.pass, true); assert.equal(JSON.parse(first.content_body).children.length, 1); });
const block = { id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', type: 'paragraph', ...JSON.parse(first.content_body).children[0] };
check(() => { const retry = planContent({ ...input, blocks: { results: [block] } }); assert.equal(retry.block_id, block.id); assert.equal(retry.revision, first.revision); assert.equal(retry.content_url, '/v1/blocks/' + block.id); assert.equal(retry.content_method, 'GET'); assert.equal(retry.content_body, ''); });
check(() => { const revised=planContent({...input,raw:{verdict:'PASS',operator_pack:PRIMARY+'\n1. Updated navigation.'},blocks:{results:[block]}}); assert.equal(revised.content_method,'PATCH'); assert.ok(!JSON.parse(revised.content_body).children); });
check(() => assert.throws(() => planContent({ ...input, blocks: { results: [block, block] } }), /Multiple/));
check(() => assert.throws(() => planContent({ ...input, blocks: { results: [], has_more: true } }), /Incomplete/));
check(() => assert.throws(() => planContent({ ...input, blocks: { results: [{ type: 'heading_3', heading_3: { rich_text: rt(PRIMARY.slice(4)) } }] } }), /Finalized/));
check(() => assert.equal(planContent({ ...input, starter_commit: '' }).pass, false));
check(() => assert.equal(planContent({ ...input, raw: { verdict: 'PASS', operator_pack: PRIMARY + '\n' + PRIMARY } }).pass, false));
check(() => assert.throws(() => propertyWrite({ ...first, saved: {} }), /durably/));
check(() => { const changed=structuredClone(block); changed.paragraph.rich_text[0].text.content+='\nHuman correction'; assert.throws(() => planContent({...input,blocks:{results:[changed]}}), /ownership/); });
check(() => { const legacy=structuredClone(block); legacy.paragraph.rich_text[0].text.content=legacy.paragraph.rich_text[0].text.content.replace(/CONTENT_SHA256:[a-f0-9]{64}\n/, ''); assert.throws(() => planContent({...input,blocks:{results:[legacy]}}), /ownership/); });
check(() => assert.throws(() => propertyWrite({ ...first, block_id:block.id, saved:{} }), /durably/));
check(() => assert.throws(() => propertyWrite({ ...first, revision:'b'.repeat(64), saved:block }), /revision/));
check(() => { const p = JSON.parse(propertyWrite({ ...first, saved: { results: [block] }, source_ref: input.source_ref }).property_body).properties; assert.equal(p['Operator Pack Block ID'].rich_text[0].text.content, block.id); for (const name of ['Pre-Record Gate', 'Submission Gate', 'Insightful Hours', 'Bootcamp Status', 'Reviewer Status']) assert.equal(p[name], undefined); });
process.stdout.write(checks + ' operator-pack checks passed\n');
