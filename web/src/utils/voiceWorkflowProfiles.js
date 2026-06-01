export const normalizeVoiceProfileId = profileOrId => {
  if (profileOrId == null || profileOrId === '') return null
  if (typeof profileOrId === 'object') return profileOrId.id ?? null
  return profileOrId
}

export const findVoiceProfile = (profiles, id) => {
  if (id == null || id === '') return null
  return (profiles || []).find(profile => String(profile.id) === String(id)) || null
}

export const formatSegmentVoiceLabel = (segment, defaultVoiceProfileId, profiles) => {
  const segmentProfile = findVoiceProfile(profiles, segment?.voice_profile_id)
  if (segmentProfile) return segmentProfile.name

  const defaultProfile = findVoiceProfile(profiles, defaultVoiceProfileId)
  if (defaultProfile) return `默认：${defaultProfile.name}`

  return '默认音色'
}
