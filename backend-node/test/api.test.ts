import request from 'supertest'
import { describe, expect, it } from 'vitest'
import { makeApp } from './helpers.js'

describe('health + archive', () => {
  it('health', async () => {
    const { app } = makeApp()
    const res = await request(app).get('/api/health')
    expect(res.status).toBe(200)
    expect(res.body.status).toBe('ok')
  })

  it('archive has the five bit instructions', async () => {
    const { app } = makeApp()
    const res = await request(app).get('/api/archive')
    const ids = new Set(res.body.instructions.map((i: { id: string }) => i.id))
    for (const id of ['contact_no', 'contact_nc', 'coil_output', 'coil_set', 'coil_reset']) {
      expect(ids.has(id)).toBe(true)
    }
  })
})

describe('PUT /api/state validation', () => {
  it('rejects an input after an output', async () => {
    const { app } = makeApp()
    const res = await request(app)
      .put('/api/state')
      .send({
        project_name: 'Invalid rung',
        instructions: [
          { instanceId: '1', instructionId: 'coil_output', address: 'Q0.0', name: 'Lamp' },
          { instanceId: '2', instructionId: 'contact_no', address: 'I0.0', name: 'Start' }
        ]
      })
    expect(res.status).toBe(422)
    expect(res.body.detail).toContain('cannot appear after an output')
  })

  it('rejects an invalid input address', async () => {
    const { app } = makeApp()
    const res = await request(app)
      .put('/api/state')
      .send({
        project_name: 'Invalid address',
        instructions: [{ instanceId: '1', instructionId: 'contact_no', address: 'I0.8', name: 'Start' }]
      })
    expect(res.status).toBe(422)
    expect(res.body.detail).toContain('I0.0 through I0.7')
  })

  it('rejects an invalid output address and unknown instruction ids', async () => {
    const { app } = makeApp()
    const badCoil = await request(app)
      .put('/api/state')
      .send({ project_name: 'x', instructions: [{ instanceId: '1', instructionId: 'coil_output', address: 'Q1.0', name: 'L' }] })
    expect(badCoil.status).toBe(422)
    expect(badCoil.body.detail).toContain('Q0.0 through Q0.7')

    const unknown = await request(app)
      .put('/api/state')
      .send({ project_name: 'x', instructions: [{ instanceId: '1', instructionId: 'nope', address: '', name: 'L' }] })
    expect(unknown.status).toBe(422)
  })

  it('rejects a blank project name', async () => {
    const { app } = makeApp()
    const res = await request(app).put('/api/state').send({ project_name: '   ', instructions: [] })
    expect(res.status).toBe(422)
  })

  it('accepts contacts then output, and round-trips hardware', async () => {
    const { app } = makeApp()
    const payload = {
      project_name: 'Valid rung',
      instructions: [
        { instanceId: '1', instructionId: 'contact_no', address: 'I0.7', name: 'Start' },
        { instanceId: '2', instructionId: 'coil_output', address: 'Q0.7', name: 'Lamp' }
      ],
      hardware: [{ id: 'h1', type: 'push_no', x: 10, y: 20, address: 'I0.7', label: 'Start' }]
    }
    const put = await request(app).put('/api/state').send(payload)
    expect(put.status).toBe(200)
    expect(put.body.status).toBe('saved')

    const get = await request(app).get('/api/state')
    expect(get.body.project_name).toBe('Valid rung')
    expect(get.body.instructions).toHaveLength(2)
    expect(get.body.hardware).toHaveLength(1)
  })

  it('returns defaults (with empty hardware) when nothing was saved or the file is old', async () => {
    const { app } = makeApp()
    const res = await request(app).get('/api/state')
    expect(res.status).toBe(200)
    expect(res.body.hardware).toEqual([])
  })

  it('answers invalid JSON with 400', async () => {
    const { app } = makeApp()
    const res = await request(app).put('/api/state').set('Content-Type', 'application/json').send('{not json')
    expect(res.status).toBe(400)
  })
})
