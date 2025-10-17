import React, { useState, useEffect } from 'react';
import { Brain, Eye, FileCode, Database, Server, Cloud, Check, Sparkles, Smartphone, Chrome, FileJson, Shield } from 'lucide-react';

const FederalFormArchitecture = () => {
  const [stage, setStage] = useState(0);
  const maxStages = 5;

  useEffect(() => {
    const handleKeyPress = (e) => {
      if (e.key === 'ArrowRight' && stage < maxStages) {
        setStage(prev => Math.min(prev + 1, maxStages));
      } else if (e.key === 'ArrowLeft' && stage > 0) {
        setStage(prev => Math.max(prev - 1, 0));
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [stage]);

  return (
    <div className="w-full min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-green-50 p-8">
      {/* Title */}
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold mb-3">
          <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-green-600 bg-clip-text text-transparent">
            Multi-Agent Federal Form Automation System
          </span>
        </h1>
        <p className="text-xl text-gray-700 max-w-5xl mx-auto">
          Vision-guided discovery + Contract-first execution = Voice-accessible government services
        </p>
      </div>

      {/* Three-Row Architecture */}
      <div className="max-w-[1400px] mx-auto space-y-4">
        
        {/* ROW 1: PHASE 1 - Discovery Flow */}
        <div className={`transition-all duration-700 ${stage >= 1 ? 'opacity-100' : 'opacity-0'}`}>
          <div className="bg-white rounded-2xl shadow-xl border-2 border-blue-300 p-6">
            <h2 className="text-2xl font-bold text-blue-800 mb-5 text-center">PHASE 1: Discovery Flow</h2>
            
            <div className="flex items-center justify-between gap-4">
              {/* FederalScout Agent */}
              <div className="flex-1 flex flex-col items-center">
                <div className="bg-blue-100 rounded-lg px-4 py-2 mb-3 border border-blue-300">
                  <p className="text-sm font-bold text-blue-800">Running on: Claude Desktop</p>
                </div>
                
                <div className="bg-gradient-to-r from-blue-500 to-purple-500 rounded-xl p-5 text-white shadow-lg w-full">
                  <div className="flex items-center justify-center gap-2 mb-2">
                    <Sparkles className="w-7 h-7" />
                    <span className="text-2xl font-bold">FederalScout Agent</span>
                  </div>
                  <p className="text-sm text-center opacity-90">Vision-guided wizard discovery</p>
                </div>
              </div>

              {/* FederalScout MCP Server */}
              <div className={`flex-1 flex flex-col items-center transition-all duration-500 ${stage >= 2 ? 'opacity-100' : 'opacity-0'}`}>
                <div className="bg-orange-100 rounded-lg px-4 py-2 mb-3 border border-orange-300">
                  <p className="text-sm font-bold text-orange-800">Running on: Local Mac (stdio)</p>
                </div>
                
                <div className="bg-orange-50 rounded-xl p-4 border-2 border-orange-300 shadow-lg w-full h-full">
                  <div className="flex items-center gap-2 mb-3">
                    <Server className="w-6 h-6 text-orange-600" />
                    <span className="text-xl font-bold text-orange-800">FederalScout MCP</span>
                  </div>
                  <div className="space-y-2">
                    <div className="bg-white rounded-lg p-2 border border-orange-200">
                      <div className="flex items-center gap-2 text-sm text-gray-800">
                        <Chrome className="w-4 h-4 text-orange-600" />
                        <span>Playwright automation</span>
                      </div>
                    </div>
                    <div className="bg-white rounded-lg p-2 border border-orange-200">
                      <div className="flex items-center gap-2 text-sm text-gray-800">
                        <Eye className="w-4 h-4 text-purple-600" />
                        <span>Claude Vision analysis</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Government Website */}
              <div className={`flex-1 flex flex-col items-center transition-all duration-500 ${stage >= 2 ? 'opacity-100' : 'opacity-0'}`}>
                <div className="bg-green-100 rounded-lg px-4 py-2 mb-3 border border-green-300">
                  <p className="text-sm font-bold text-green-800">Running on: studentaid.gov</p>
                </div>
                
                <div className="bg-green-50 rounded-xl p-4 border-2 border-green-300 shadow-lg w-full h-full">
                  <div className="flex items-center gap-2 mb-3">
                    <Chrome className="w-6 h-6 text-green-600" />
                    <span className="text-xl font-bold text-green-800">Government Website</span>
                  </div>
                  <div className="bg-white rounded-lg p-3 border-2 border-green-200 mb-2">
                    <p className="text-xs font-mono text-green-700 break-all">
                      studentaid.gov/aid-estimator/
                    </p>
                  </div>
                  <p className="text-sm text-gray-700 font-semibold">FSA Student Aid Estimator</p>
                  <p className="text-xs text-gray-600 mt-1">6 pages, 47 fields</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ROW 2: Contract-First Artifacts - COMPACT */}
        <div className={`transition-all duration-700 ${stage >= 3 ? 'opacity-100' : 'opacity-0'}`}>
          <div className="bg-purple-50 rounded-2xl shadow-xl border-2 border-purple-300 p-4">
            <h2 className="text-xl font-bold text-purple-800 mb-3 text-center">Contract-First Artifacts</h2>
            
            <div className="flex items-stretch justify-center gap-4">
              {/* Artifact 1: Wizard Structure */}
              <div className="flex-1 max-w-lg">
                <div className="bg-gradient-to-br from-blue-100 to-cyan-100 rounded-xl p-4 shadow-lg border-2 border-blue-400 h-full">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center">
                      <FileCode className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <h4 className="text-lg font-bold text-blue-900">Wizard Structure</h4>
                      <p className="text-xs text-blue-700">Playwright execution instructions</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Artifact 2: User Data Schema - THE CONTRACT */}
              <div className="flex-1 max-w-lg">
                <div className="bg-gradient-to-br from-green-100 to-emerald-100 rounded-xl p-4 shadow-lg border-2 border-green-400 h-full">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center">
                      <Shield className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <h4 className="text-lg font-bold text-green-900">User Data Schema</h4>
                      <p className="text-xs text-green-700 font-bold">THE CONTRACT - Defines required user data</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ROW 3: PHASE 2 - Execution Flow */}
        <div className={`transition-all duration-700 ${stage >= 4 ? 'opacity-100' : 'opacity-0'}`}>
          <div className="bg-white rounded-2xl shadow-xl border-2 border-green-300 p-6">
            <h2 className="text-2xl font-bold text-green-800 mb-5 text-center">PHASE 2: Execution Flow</h2>
            
            <div className="flex items-center justify-between gap-4">
              {/* FederalRunner Agent on Claude Mobile */}
              <div className="flex-1 flex flex-col items-center">
                <div className="bg-blue-100 rounded-lg px-4 py-2 mb-3 border border-blue-300">
                  <p className="text-sm font-bold text-blue-800">Running on: Claude.ai / Claude Mobile</p>
                </div>
                
                <div className="bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl p-5 text-white shadow-lg w-full">
                  <div className="flex items-center justify-center gap-2 mb-2">
                    <Sparkles className="w-7 h-7" />
                    <span className="text-2xl font-bold">FederalRunner Agent</span>
                  </div>
                  <p className="text-sm text-center opacity-90 mb-3">Atomic wizard execution</p>
                  <div className="bg-white/20 rounded-lg p-3">
                    <p className="text-xs italic text-center">
                      "Hey Claude, calculate my federal student aid. I'm 17..."
                    </p>
                  </div>
                </div>
              </div>

              {/* FederalRunner MCP Server */}
              <div className={`flex-1 flex flex-col items-center transition-all duration-500 ${stage >= 5 ? 'opacity-100' : 'opacity-0'}`}>
                <div className="bg-green-100 rounded-lg px-4 py-2 mb-3 border border-green-300">
                  <p className="text-sm font-bold text-green-800">Running on: Google Cloud Run</p>
                </div>
                
                <div className="bg-green-50 rounded-xl p-4 border-2 border-green-300 shadow-lg w-full h-full">
                  <div className="flex items-center gap-2 mb-3">
                    <Server className="w-6 h-6 text-green-600" />
                    <span className="text-xl font-bold text-green-800">FederalRunner MCP</span>
                  </div>
                  <div className="flex items-center gap-2 mb-3">
                    <Cloud className="w-5 h-5 text-blue-600" />
                    <p className="text-sm text-gray-600">HTTP + OAuth 2.1</p>
                  </div>
                  <div className="space-y-2">
                    <div className="bg-white rounded-lg p-2 border border-green-200">
                      <div className="flex items-center gap-2 text-sm text-gray-800">
                        <Shield className="w-4 h-4 text-green-600" />
                        <span>Schema validation</span>
                      </div>
                    </div>
                    <div className="bg-white rounded-lg p-2 border border-green-200">
                      <div className="flex items-center gap-2 text-sm text-gray-800">
                        <Chrome className="w-4 h-4 text-orange-600" />
                        <span>Playwright headless</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Government Website + Auth0 Column */}
              <div className={`flex-1 space-y-3 transition-all duration-500 ${stage >= 5 ? 'opacity-100' : 'opacity-0'}`}>
                {/* Government Website */}
                <div className="flex flex-col items-center">
                  <div className="bg-orange-100 rounded-lg px-4 py-2 mb-3 border border-orange-300">
                    <p className="text-sm font-bold text-orange-800">Running on: studentaid.gov</p>
                  </div>
                  
                  <div className="bg-orange-50 rounded-xl p-4 border-2 border-orange-300 shadow-lg w-full">
                    <div className="flex items-center gap-2 mb-2">
                      <Chrome className="w-6 h-6 text-orange-600" />
                      <span className="text-xl font-bold text-orange-800">Gov't Website</span>
                    </div>
                    <div className="bg-white rounded-lg p-2 border-2 border-orange-200 mb-2">
                      <p className="text-xs font-mono text-orange-700 break-all">
                        studentaid.gov/aid-estimator/
                      </p>
                    </div>
                    <p className="text-sm text-gray-700">Atomic: 8 sec</p>
                  </div>
                </div>

                {/* Auth0 */}
                <div className="flex flex-col items-center">
                  <div className="bg-purple-100 rounded-lg px-4 py-2 mb-3 border border-purple-300">
                    <p className="text-sm font-bold text-purple-800">Running on: Auth0 Cloud</p>
                  </div>
                  
                  <div className="bg-purple-50 rounded-xl p-4 border-2 border-purple-300 shadow-lg w-full">
                    <div className="flex items-center gap-2 mb-2">
                      <Shield className="w-6 h-6 text-purple-600" />
                      <span className="text-xl font-bold text-purple-800">Auth0</span>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">OAuth 2.1 + DCR</p>
                    <div className="bg-white rounded-lg p-2 border border-purple-200 text-xs text-gray-700">
                      Token validation
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* Bottom: Key Innovation Summary */}
      <div className={`mt-6 max-w-[1400px] mx-auto transition-all duration-700 ${stage >= 5 ? 'opacity-100' : 'opacity-0'}`}>
        <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-2xl shadow-xl border-2 border-purple-300 p-5">
          <h3 className="text-2xl font-bold text-purple-900 mb-2 text-center">Contract-First Pattern Innovation</h3>
          <p className="text-center text-gray-700 mb-4">
            Discovery generates contract → Claude collects data naturally → Execution validates & runs
          </p>
          <div className="flex justify-center gap-8">
            <div className="flex items-center gap-2">
              <Check className="w-5 h-5 text-green-600" />
              <span className="text-sm font-semibold text-gray-800">No hardcoded mappers</span>
            </div>
            <div className="flex items-center gap-2">
              <Check className="w-5 h-5 text-green-600" />
              <span className="text-sm font-semibold text-gray-800">Universal tools</span>
            </div>
            <div className="flex items-center gap-2">
              <Check className="w-5 h-5 text-green-600" />
              <span className="text-sm font-semibold text-gray-800">Voice-first mobile</span>
            </div>
            <div className="flex items-center gap-2">
              <Check className="w-5 h-5 text-green-600" />
              <span className="text-sm font-semibold text-gray-800">MCP stdio + HTTP</span>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation hint */}
      <div className="text-center mt-4">
        <p className="text-sm text-gray-500">Use ← → arrow keys | Stage {stage + 1} of {maxStages + 1}</p>
      </div>
    </div>
  );
};

export default FederalFormArchitecture;