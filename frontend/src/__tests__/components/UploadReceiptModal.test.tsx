import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('@/lib/api', () => ({
  api: { postForm: vi.fn() },
}))

import { UploadReceiptModal } from '@/components/UploadReceiptModal'
import { api } from '@/lib/api'

const bill = { id: 'bill-1', name: 'Água' }

function renderModal(onClose = vi.fn(), onSuccess = vi.fn()) {
  render(<UploadReceiptModal bill={bill} onClose={onClose} onSuccess={onSuccess} />)
  return { onClose, onSuccess }
}

function pdfFile(name = 'comprovante.pdf') {
  return new File(['%PDF-fake'], name, { type: 'application/pdf' })
}

describe('UploadReceiptModal', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows the bill name and defaults the select to the current month', () => {
    renderModal()
    expect(screen.getByText(/Água/)).toBeInTheDocument()
    const select = screen.getByRole('combobox') as HTMLSelectElement
    expect(Number(select.value)).toBe(new Date().getMonth() + 1)
  })

  it('keeps submit disabled until a file is chosen', async () => {
    renderModal()
    const submit = screen.getByRole('button', { name: 'Enviar' })
    expect(submit).toBeDisabled()

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, pdfFile())

    expect(screen.getByText('comprovante.pdf')).toBeInTheDocument()
    expect(submit).toBeEnabled()
  })

  it('posts the file and chosen month, then calls onSuccess', async () => {
    vi.mocked(api.postForm).mockResolvedValue({ ok: true } as Response)
    const { onSuccess } = renderModal()

    await userEvent.selectOptions(screen.getByRole('combobox'), '3')
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, pdfFile())
    await userEvent.click(screen.getByRole('button', { name: 'Enviar' }))

    await waitFor(() => expect(onSuccess).toHaveBeenCalled())
    const [path, body] = vi.mocked(api.postForm).mock.calls[0]
    expect(path).toBe('/api/bills/bill-1/receipt')
    expect((body as FormData).get('month')).toBe('3')
    expect(((body as FormData).get('file') as File).name).toBe('comprovante.pdf')
  })

  it('shows the API error detail when the upload fails', async () => {
    vi.mocked(api.postForm).mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: 'Arquivo maior que 10 MB' }),
    } as Response)
    const { onSuccess } = renderModal()

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, pdfFile())
    await userEvent.click(screen.getByRole('button', { name: 'Enviar' }))

    await waitFor(() =>
      expect(screen.getByText('Arquivo maior que 10 MB')).toBeInTheDocument(),
    )
    expect(onSuccess).not.toHaveBeenCalled()
  })

  it('shows a network error message when the request throws', async () => {
    vi.mocked(api.postForm).mockRejectedValue(new Error('offline'))
    renderModal()

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, pdfFile())
    await userEvent.click(screen.getByRole('button', { name: 'Enviar' }))

    await waitFor(() =>
      expect(screen.getByText(/Verifique sua conexão/)).toBeInTheDocument(),
    )
  })
})
