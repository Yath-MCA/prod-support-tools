import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen flex items-center justify-center p-6">
          <div className="max-w-md rounded-xl border border-red-200 bg-red-50 dark:bg-red-950 dark:border-red-800 p-6">
            <h1 className="text-lg font-semibold text-red-800 dark:text-red-200">Something went wrong</h1>
            <p className="mt-2 text-sm text-red-700 dark:text-red-300">{this.state.error.message}</p>
            <button
              type="button"
              className="mt-4 text-sm text-blue-600 hover:underline"
              onClick={() => window.location.reload()}
            >
              Reload
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
