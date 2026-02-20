"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { api, Repo, FileItem, ChatMessage } from "@/lib/api";
import {
  Folder,
  File,
  Send,
  Settings,
  ChevronRight,
  ChevronDown,
  Loader2,
  Square,
  X,
  Trash2,
  Key,
  Check,
  LogOut,
  RefreshCw,
  Database,
  Sparkles,
} from "lucide-react";
import toast, { Toaster } from "react-hot-toast";
import dynamic from "next/dynamic";
import {
  Group,
  Panel,
  Separator,
} from "react-resizable-panels";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

const PROVIDERS = [
  { id: "cerebras", label: "Cerebras (Fast!)", model: "llama3.1-8b" },
  { id: "openai", label: "GPT-4o", model: "gpt-4o" },
  { id: "anthropic", label: "Claude 3.5 Sonnet", model: "claude-3-5-sonnet-20241022" },
  { id: "gemini", label: "Gemini 2.0 Flash", model: "gemini-flash-latest" },
] as const;

type ProviderId = (typeof PROVIDERS)[number]["id"];
type KeyState = Record<ProviderId, string>;
type KeysConfigured = Record<string, boolean>;

function getLanguage(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase() || "";
  const map: Record<string, string> = {
    ts: "typescript", tsx: "typescript", js: "javascript", jsx: "javascript",
    py: "python", rs: "rust", go: "go", java: "java", cpp: "cpp", c: "c",
    cs: "csharp", rb: "ruby", php: "php", html: "html", css: "css",
    scss: "scss", json: "json", yaml: "yaml", yml: "yaml", md: "markdown",
    sh: "shell", toml: "ini", xml: "xml", sql: "sql",
  };
  return map[ext] || "plaintext";
}

export default function Dashboard() {
  const searchParams = useSearchParams();
  const [token, setToken] = useState<string | null>(null);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<Repo | null>(null);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [isIndexing, setIsIndexing] = useState(false);
  const [isScaffolding, setIsScaffolding] = useState(false);
  const [projectMode, setProjectMode] = useState<"web" | "react-native">("web");
  const [currentPath, setCurrentPath] = useState("");
  const [pathStack, setPathStack] = useState<string[]>([]);
  const [fileContent, setFileContent] = useState<string>("");
  const [selectedFile, setSelectedFile] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streamingContent, setStreamingContent] = useState<string>("");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [provider, setProvider] = useState<ProviderId>("cerebras");
  const [showSettings, setShowSettings] = useState(false);
  const [keysConfigured, setKeysConfigured] = useState<KeysConfigured>({});
  const [keyInputs, setKeyInputs] = useState<KeyState>({ cerebras: "", openai: "", anthropic: "", gemini: "" });
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState<string>("");
  const [repoSearch, setRepoSearch] = useState("");
  const [lastUsage, setLastUsage] = useState<{ prompt_tokens: number; completion_tokens: number; total_tokens: number } | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  // Token init
  useEffect(() => {
    const tokenParam = searchParams.get("token");
    if (tokenParam) {
      localStorage.setItem("token", tokenParam);
      setToken(tokenParam);
      window.history.replaceState({}, "", "/dashboard");
    } else {
      const stored = localStorage.getItem("token");
      if (stored) setToken(stored);
    }
  }, [searchParams]);

  useEffect(() => {
    if (token) {
      loadRepos();
      loadKeys();
    }
  }, [token]);

  async function loadRepos(search?: string) {
    try {
      const data = await api.getRepos(search);
      setRepos(data.repos);
    } catch (err: any) {
      toast.error("Failed to load repos: " + err.message);
    }
  }

  async function loadKeys() {
    try {
      const keys = await api.getKeys();
      setKeysConfigured(keys as any);
    } catch (err) { }
  }

  async function loadContents(path: string = "") {
    if (!selectedRepo) return;
    try {
      const data = await api.getContents(selectedRepo.owner.login, selectedRepo.name, path);
      const items = Array.isArray(data) ? data : [data];
      setFiles(items.sort((a, b) => {
        if (a.type === "dir" && b.type !== "dir") return -1;
        if (a.type !== "dir" && b.type === "dir") return 1;
        return a.name.localeCompare(b.name);
      }));
      setCurrentPath(path);
    } catch (err: any) {
      toast.error("Failed to load files: " + err.message);
    }
  }

  async function loadFile(path: string) {
    if (!selectedRepo) return;
    try {
      const data = await api.getFileContent(selectedRepo.owner.login, selectedRepo.name, path);
      setFileContent(data.content);
      setEditedContent(data.content);
      setSelectedFile(path);
      setIsEditing(false);
    } catch (err: any) {
      toast.error("Failed to load file: " + err.message);
    }
  }

  const handleSelectRepo = useCallback(async (repo: Repo) => {
    setSelectedRepo(repo);
    setFiles([]);
    setFileContent("");
    setSelectedFile("");
    setMessages([]);
    setSessionId(null);
    setCurrentPath("");
    setPathStack([]);
    try {
      const data = await api.getContents(repo.owner.login, repo.name, "");
      const items = Array.isArray(data) ? data : [data];
      setFiles(items.sort((a, b) => {
        if (a.type === "dir" && b.type !== "dir") return -1;
        if (a.type !== "dir" && b.type === "dir") return 1;
        return a.name.localeCompare(b.name);
      }));
    } catch (err: any) {
      toast.error("Failed to load repo: " + err.message);
    }
  }, []);

  function navigateTo(path: string) {
    setPathStack((prev) => [...prev, currentPath]);
    loadContents(path);
  }

  function navigateBack() {
    const prev = pathStack[pathStack.length - 1] ?? "";
    setPathStack((s) => s.slice(0, -1));
    loadContents(prev);
  }

  async function sendMessage() {
    if (!input.trim() || !selectedRepo) return;
    const userMsg: ChatMessage = { role: "user", content: input };
    const contextMsg: ChatMessage = {
      role: "system",
      content: `You are an expert coding assistant helping with the GitHub repository "${selectedRepo.full_name}".${selectedFile ? ` The user is currently viewing the file: ${selectedFile}.` : ""} Be concise and helpful.`,
    };
    const history = [...messages, userMsg];
    setMessages(history);
    setInput("");
    setLoading(true);
    setStreamingContent("");

    const providerInfo = PROVIDERS.find((p) => p.id === provider)!;
    abortRef.current = new AbortController();

    try {
      let accumulated = "";
      const result = await api.chatStream(
        [contextMsg, ...history],
        provider,
        { model: providerInfo.model, repo: selectedRepo.full_name, session_id: sessionId ?? undefined },
        (chunk) => {
          accumulated += chunk;
          setStreamingContent(accumulated);
        },
        (usage) => {
          setLastUsage(usage);
        },
        abortRef.current.signal
      );
      setSessionId(result.session_id);
      setMessages([...history, { role: "assistant", content: accumulated }]);
    } catch (err: any) {
      if (err.name === "AbortError") {
        toast("Response cancelled.");
      } else {
        toast.error("AI error: " + err.message);
        // Remove the optimistically added user message on error
        setMessages(messages);
      }
    } finally {
      setStreamingContent("");
      setLoading(false);
      abortRef.current = null;
    }
  }

  function stopStreaming() {
    abortRef.current?.abort();
  }

  async function saveApiKey(providerName: ProviderId) {
    const key = keyInputs[providerName];
    if (!key.trim()) return;
    try {
      await api.setKey(providerName, key);
      setKeyInputs((prev) => ({ ...prev, [providerName]: "" }));
      await loadKeys();
      toast.success(`${providerName} API key saved!`);
    } catch (err: any) {
      toast.error("Failed to save key: " + err.message);
    }
  }

  async function deleteApiKey(providerName: string) {
    try {
      await api.deleteKey(providerName);
      await loadKeys();
      toast.success(`${providerName} key removed.`);
    } catch (err: any) {
      toast.error("Failed to remove key: " + err.message);
    }
  }
  async function handleIndexRepo() {
    if (!selectedRepo) return;
    setIsIndexing(true);
    try {
      await api.indexRepo(selectedRepo.owner.login, selectedRepo.name);
      toast.success("Indexing started! Axel will soon know your whole codebase.");
    } catch (err: any) {
      toast.error("Failed to start indexing: " + err.message);
    } finally {
      setIsIndexing(false);
    }
  }

  async function handleScaffold() {
    if (!selectedRepo) return;
    setIsScaffolding(true);
    try {
      const result = await api.scaffoldRepo(selectedRepo.owner.login, selectedRepo.name, projectMode);
      toast.success(`${projectMode} scaffolded in branch ${result.branch}!`);
    } catch (err: any) {
      toast.error("Scaffolding failed: " + err.message);
    } finally {
      setIsScaffolding(false);
    }
  }

  function signOut() {
    localStorage.removeItem("token");
    window.location.href = "/";
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!loading) sendMessage();
    }
  }

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center space-y-4">
          <p className="text-lg text-gray-600">Please sign in to continue</p>
          <a href="/" className="text-blue-600 hover:underline">← Back to Home</a>
        </div>
      </div>
    );
  }

  const currentProviderInfo = PROVIDERS.find((p) => p.id === provider)!;

  return (
    <div className="h-screen flex flex-col bg-white font-sans">
      <Toaster position="top-right" />

      {/* Header */}
      <header className="h-12 border-b flex items-center px-3 gap-3 bg-gray-950 text-white flex-shrink-0">
        <span className="font-bold text-lg tracking-tight text-white">Axel</span>
        <div className="h-5 w-px bg-gray-700" />

        {/* Repo selector */}
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <select
            className="bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1 max-w-xs truncate cursor-pointer"
            onChange={(e) => {
              const repo = repos.find((r) => r.full_name === e.target.value);
              if (repo) handleSelectRepo(repo);
            }}
            value={selectedRepo?.full_name || ""}
          >
            <option value="">Select a repository…</option>
            {repos.map((repo) => (
              <option key={repo.id} value={repo.full_name}>{repo.full_name}</option>
            ))}
          </select>
          <button onClick={() => loadRepos()} title="Refresh repos" className="text-gray-400 hover:text-white transition-colors mr-2">
            <RefreshCw className="h-4 w-4" />
          </button>

          {selectedRepo && (
            <>
              <button
                onClick={handleIndexRepo}
                disabled={isIndexing}
                title="Index codebase for RAG"
                className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs transition-colors ${isIndexing ? "bg-blue-900 text-blue-200" : "bg-gray-800 text-gray-300 hover:bg-gray-700 hover:text-white"}`}
              >
                {isIndexing ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Database className="h-3.5 w-3.5" />
                )}
                <span>{isIndexing ? "Indexing..." : "Index"}</span>
              </button>

              {projectMode !== "web" && (
                <button
                  onClick={handleScaffold}
                  disabled={isScaffolding}
                  title={`Scaffold ${projectMode} project`}
                  className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs transition-colors ${isScaffolding ? "bg-purple-900 text-purple-200" : "bg-purple-600 text-white hover:bg-purple-700"}`}
                >
                  {isScaffolding ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Sparkles className="h-3.5 w-3.5" />
                  )}
                  <span>{isScaffolding ? "Scaffolding..." : "Scaffold"}</span>
                </button>
              )}
            </>
          )}
        </div>

        {/* Project Mode selector */}
        <select
          className="bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1 cursor-pointer"
          value={projectMode}
          onChange={(e) => setProjectMode(e.target.value as "web" | "react-native")}
        >
          <option value="web">Web Mode</option>
          <option value="react-native">React Native Mode</option>
        </select>

        {/* Provider selector */}
        <select
          className="bg-gray-800 border border-gray-700 text-white text-sm rounded px-2 py-1 cursor-pointer"
          value={provider}
          onChange={(e) => setProvider(e.target.value as ProviderId)}
        >
          {PROVIDERS.map((p) => (
            <option key={p.id} value={p.id}>{p.label}</option>
          ))}
        </select>

        <button
          onClick={() => setShowSettings(!showSettings)}
          className={`p-1.5 rounded transition-colors ${showSettings ? "bg-gray-700 text-white" : "text-gray-400 hover:text-white"}`}
          title="Settings"
        >
          <Key className="h-4 w-4" />
        </button>
        <button onClick={signOut} title="Sign out" className="text-gray-400 hover:text-white transition-colors">
          <LogOut className="h-4 w-4" />
        </button>
      </header >

      {/* Settings Panel */}
      {
        showSettings && (
          <div className="border-b bg-gray-50 px-4 py-3 flex-shrink-0">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-sm">API Keys</h3>
              <button onClick={() => setShowSettings(false)} className="text-gray-400 hover:text-gray-600">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {PROVIDERS.map((p) => (
                <div key={p.id} className="flex items-center gap-2">
                  <span className="text-sm w-24 text-gray-600 flex-shrink-0">{p.label.split(" ")[0]}:</span>
                  {keysConfigured[p.id] ? (
                    <div className="flex items-center gap-2">
                      <Check className="h-4 w-4 text-green-500" />
                      <span className="text-xs text-green-600">Configured</span>
                      <button
                        onClick={() => deleteApiKey(p.id)}
                        className="text-xs text-red-500 hover:text-red-700 flex items-center gap-1"
                      >
                        <Trash2 className="h-3 w-3" /> Remove
                      </button>
                    </div>
                  ) : (
                    <div className="flex gap-1 flex-1">
                      <input
                        type="password"
                        placeholder={`Enter ${p.label.split(" ")[0]} key…`}
                        className="border rounded px-2 py-1 text-sm flex-1 min-w-0"
                        value={keyInputs[p.id]}
                        onChange={(e) => setKeyInputs((prev) => ({ ...prev, [p.id]: e.target.value }))}
                        onKeyDown={(e) => e.key === "Enter" && saveApiKey(p.id)}
                      />
                      <button
                        onClick={() => saveApiKey(p.id)}
                        disabled={!keyInputs[p.id].trim()}
                        className="bg-blue-600 text-white px-2 py-1 rounded text-sm hover:bg-blue-700 disabled:opacity-40"
                      >
                        Save
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )
      }

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        <Group orientation="horizontal" id="main-group">
          {/* File Tree Sidebar */}
          <Panel id="file-tree" defaultSize={50} minSize={10} maxSize={200} collapsible>
            <div className="h-full border-r bg-gray-50 flex flex-col overflow-hidden">
              {selectedRepo ? (
                <>
                  <div className="flex items-center gap-1 px-2 py-1.5 border-b bg-gray-100 text-xs text-gray-500 flex-shrink-0">
                    {pathStack.length > 0 && (
                      <button onClick={navigateBack} className="hover:text-gray-800 font-mono">../</button>
                    )}
                    <span className="truncate">{currentPath || selectedRepo.name}</span>
                  </div>
                  <div className="flex-1 overflow-y-auto py-1">
                    {files.map((file) => (
                      <button
                        key={file.path}
                        onClick={() => {
                          if (file.type === "dir") {
                            navigateTo(file.path);
                          } else {
                            loadFile(file.path);
                          }
                        }}
                        className={`flex items-center gap-1.5 w-full text-left px-3 py-1 text-xs hover:bg-gray-200 transition-colors truncate ${selectedFile === file.path ? "bg-blue-50 text-blue-700 font-medium" : "text-gray-700"
                          }`}
                      >
                        {file.type === "dir" ? (
                          <Folder className="h-3.5 w-3.5 text-yellow-500 flex-shrink-0" />
                        ) : (
                          <File className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
                        )}
                        <span className="truncate">{file.name}</span>
                      </button>
                    ))}
                  </div>
                </>
              ) : (
                <div className="flex-1 flex items-center justify-center text-xs text-gray-400 p-4 text-center">
                  Select a repository to browse files
                </div>
              )}
            </div>
          </Panel>

          <Separator id="sep-1" className="w-1 bg-gray-200 hover:bg-blue-400 transition-colors cursor-col-resize" />

          {/* Editor */}
          <Panel id="editor" defaultSize={50} minSize={10}>
            <div className="h-full flex flex-col min-w-0 overflow-hidden">
              {selectedFile ? (
                <>
                  <div className="flex items-center justify-between px-3 py-1.5 border-b bg-gray-50 flex-shrink-0">
                    <span className="text-xs text-gray-500 font-mono truncate">{selectedFile}</span>
                    <button
                      onClick={() => setIsEditing(!isEditing)}
                      className={`text-xs px-2 py-0.5 rounded border transition-colors ${isEditing ? "bg-blue-600 text-white border-blue-600" : "border-gray-300 text-gray-600 hover:bg-gray-100"
                        }`}
                    >
                      {isEditing ? "Editing" : "View"}
                    </button>
                  </div>
                  <div className="flex-1 min-h-0">
                    <MonacoEditor
                      height="100%"
                      language={getLanguage(selectedFile)}
                      value={isEditing ? editedContent : fileContent}
                      onChange={(val) => isEditing && setEditedContent(val || "")}
                      options={{
                        readOnly: !isEditing,
                        minimap: { enabled: false },
                        fontSize: 13,
                        lineNumbers: "on",
                        scrollBeyondLastLine: false,
                        wordWrap: "on",
                        theme: "vs",
                        automaticLayout: true,
                      }}
                    />
                  </div>
                </>
              ) : (
                <div className="flex-1 flex items-center justify-center text-gray-300 text-sm select-none">
                  {selectedRepo ? "← Select a file to view" : "← Select a repo, then a file"}
                </div>
              )}
            </div>
          </Panel>

          <Separator id="sep-2" className="w-1 bg-gray-200 hover:bg-blue-400 transition-colors cursor-col-resize" />

          {/* Chat Panel */}
          <Panel id="chat" defaultSize={30} minSize={5}>
            <div className="h-full border-l flex flex-col overflow-hidden bg-white">
              {/* Chat Header with Tokens */}
              <div className="h-9 border-b bg-gray-50 flex items-center justify-between px-3 flex-shrink-0">
                <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider text-gray-600">Chat</span>
                {lastUsage && (
                  <div className="flex items-center gap-2 text-[10px] text-gray-400 font-mono">
                    <span title="Prompt tokens">P: {lastUsage.prompt_tokens}</span>
                    <span title="Completion tokens">C: {lastUsage.completion_tokens}</span>
                    <span className="text-blue-600 font-bold" title="Total tokens">T: {lastUsage.total_tokens}</span>
                  </div>
                )}
              </div>
              {/* Chat messages */}
              <div className="flex-1 overflow-y-auto px-3 py-2 space-y-3 min-h-0">
                {messages.length === 0 && !streamingContent && (
                  <div className="h-full flex flex-col items-center justify-center text-gray-300 text-xs text-center gap-2 pt-8">
                    <span className="text-2xl">💬</span>
                    <p>Ask anything about your code.</p>
                    {!selectedRepo && <p className="text-gray-400">Select a repo first.</p>}
                  </div>
                )}
                {messages.map((msg, i) => (
                  <div key={i} className={`flex flex-col gap-0.5 ${msg.role === "user" ? "items-end" : "items-start"}`}>
                    <span className="text-[10px] text-gray-400 px-1">{msg.role === "user" ? "You" : currentProviderInfo.label}</span>
                    <div
                      className={`max-w-full px-3 py-2 rounded-lg text-sm whitespace-pre-wrap break-words ${msg.role === "user"
                        ? "bg-blue-600 text-white rounded-tr-sm"
                        : "bg-gray-100 text-gray-800 rounded-tl-sm"
                        }`}
                    >
                      {msg.content}
                    </div>
                  </div>
                ))}
                {streamingContent && (
                  <div className="flex flex-col gap-0.5 items-start">
                    <span className="text-[10px] text-gray-400 px-1">{currentProviderInfo.label}</span>
                    <div className="max-w-full px-3 py-2 rounded-lg rounded-tl-sm text-sm whitespace-pre-wrap break-words bg-gray-100 text-gray-800">
                      {streamingContent}
                      <span className="inline-block w-1 h-3.5 bg-blue-500 ml-0.5 animate-pulse align-middle" />
                    </div>
                  </div>
                )}
                {loading && !streamingContent && (
                  <div className="flex items-center gap-2 text-gray-400 text-xs">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span>{currentProviderInfo.label} is thinking…</span>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Input */}
              <div className="border-t p-2 flex-shrink-0">
                <div className="flex gap-1.5 items-end">
                  <textarea
                    ref={textareaRef}
                    rows={2}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={selectedRepo ? "Ask about your code… (Enter to send)" : "Select a repo first"}
                    className="flex-1 border rounded px-2 py-1.5 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
                    disabled={loading || !selectedRepo}
                    style={{ maxHeight: 120 }}
                  />
                  {loading ? (
                    <button
                      onClick={stopStreaming}
                      className="bg-red-500 text-white p-2 rounded hover:bg-red-600 flex-shrink-0"
                      title="Stop"
                    >
                      <Square className="h-4 w-4" />
                    </button>
                  ) : (
                    <button
                      onClick={sendMessage}
                      disabled={loading || !selectedRepo || !input.trim()}
                      className="bg-blue-600 text-white p-2 rounded hover:bg-blue-700 disabled:opacity-40 flex-shrink-0"
                      title="Send (Enter)"
                    >
                      <Send className="h-4 w-4" />
                    </button>
                  )}
                </div>
                {messages.length > 0 && (
                  <button
                    onClick={() => { setMessages([]); setSessionId(null); setStreamingContent(""); setLastUsage(null); }}
                    className="mt-1 text-[10px] text-gray-400 hover:text-red-500 flex items-center gap-1"
                  >
                    <Trash2 className="h-3 w-3" /> Clear chat
                  </button>
                )}
              </div>
            </div>
          </Panel>
        </Group>
      </div>
    </div >
  );
}
