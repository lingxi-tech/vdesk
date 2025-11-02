import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ContainerList from '../src/components/ContainerList.vue'

describe('ContainerList', () => {
  it('renders create form and table', () => {
    const wrapper = mount(ContainerList)
    expect(wrapper.text()).toContain('Create Container')
    expect(wrapper.text()).toContain('Containers')
  })
})
