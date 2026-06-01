import test from 'node:test'
import assert from 'node:assert/strict'

import {
  findVoiceProfile,
  formatSegmentVoiceLabel,
  normalizeVoiceProfileId,
} from './voiceWorkflowProfiles.js'

const PROFILES = [
  { id: 1, name: '温柔女旁白' },
  { id: 2, name: '少年男声' },
]

test('normalizeVoiceProfileId stores only the selected profile id', () => {
  assert.equal(normalizeVoiceProfileId({ id: 2, name: '少年男声' }), 2)
  assert.equal(normalizeVoiceProfileId(1), 1)
  assert.equal(normalizeVoiceProfileId(null), null)
})

test('findVoiceProfile supports numeric and string ids', () => {
  assert.deepEqual(findVoiceProfile(PROFILES, '2'), PROFILES[1])
  assert.equal(findVoiceProfile(PROFILES, null), null)
})

test('formatSegmentVoiceLabel shows per-segment profile before workflow default', () => {
  assert.equal(
    formatSegmentVoiceLabel({ voice_profile_id: 2 }, 1, PROFILES),
    '少年男声',
  )
  assert.equal(
    formatSegmentVoiceLabel({ voice_profile_id: null }, 1, PROFILES),
    '默认：温柔女旁白',
  )
  assert.equal(
    formatSegmentVoiceLabel({ voice_profile_id: null }, null, PROFILES),
    '默认音色',
  )
})
