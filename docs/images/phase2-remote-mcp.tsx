import React, { useState, useEffect } from 'react';
import { Brain, Server, Cloud, Sparkles, Smartphone, Chrome, Shield } from 'lucide-react';

const Phase2RemoteMCP = () => {
  const [stage, setStage] = useState(0);
  const maxStages = 4;

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
            Phase 2: Remote MCP Server Architecture
          </span>
        </h1>
        <p className="text-xl text-gray-700 max-w-5xl mx-auto">
          Voice-accessible execution via Claude Mobile with OAuth 2.1 security
        </p>
      </div>

      {/* Phase 2 Content */}
      <div className="max-w-[1400px] mx-auto">
        <div className={`transition-all duration-700 ${stage >= 0 ? 'opacity-100' : 'opacity-0'}`}>
          <div className="bg-white rounded-2xl shadow-xl border-2 border-green-300 p-6">
            
            <div className="flex items-center justify-between px-8">
              {/* Left column: User Query + FederalRunner Agent */}
              <div className="w-[380px] flex flex-col items-center gap-4">
                {/* User Query Box */}
                <div className={`transition-all duration-500 ${stage >= 1 ? 'opacity-100' : 'opacity-0'} w-full`}>
                  <div className="bg-gradient-to-r from-pink-100 to-purple-100 rounded-xl p-4 border-2 border-pink-300 shadow-lg">
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 bg-pink-400 rounded-full flex items-center justify-center flex-shrink-0">
                        <Smartphone className="w-6 h-6 text-white" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-gray-800 mb-1">Voice Query</p>
                        <p className="text-sm italic text-gray-700">
                          "Hey Claude, calculate my federal student aid. I'm 17..."
                        </p>
                      </div>
                    </div>
                  </div>
                  
                  {/* Down Arrow */}
                  <div className="flex justify-center my-2">
                    <div className="text-blue-500">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                        <path d="M12 5v14M19 12l-7 7-7-7"/>
                      </svg>
                    </div>
                  </div>
                </div>

                {/* FederalRunner Agent */}
                <div className={`transition-all duration-500 ${stage >= 2 ? 'opacity-100' : 'opacity-0'} w-full`}>
                  <div className="bg-blue-100 rounded-lg px-4 py-2 mb-3 border border-blue-300">
                    <p className="text-sm font-bold text-blue-800">Running on: Claude.ai / Claude Mobile</p>
                  </div>
                  
                  <div className="bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl p-5 text-white shadow-lg">
                    <div className="flex items-center justify-center gap-2 mb-3">
                      <Sparkles className="w-7 h-7" />
                      <span className="text-2xl font-bold">FederalRunner Agent</span>
                    </div>
                    <div className="space-y-2">
                      <div className="bg-white/20 rounded-lg p-2">
                        <div className="flex items-center gap-2 text-sm">
                          <Brain className="w-4 h-4" />
                          <span className="font-semibold">Natural Conversation:</span>
                        </div>
                        <p className="text-xs ml-6 opacity-90">Collects user data conversationally</p>
                      </div>
                      <div className="bg-white/20 rounded-lg p-2">
                        <div className="flex items-center gap-2 text-sm">
                          <Smartphone className="w-4 h-4" />
                          <span className="font-semibold">Voice-First:</span>
                        </div>
                        <p className="text-xs ml-6 opacity-90">Mobile access, hands-free execution</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Arrow from Agent to MCP */}
              <div className={`flex items-center px-2 transition-all duration-500 ${stage >= 3 ? 'opacity-100' : 'opacity-0'}`}>
                <div className="text-blue-500">
                  <svg width="36" height="24" viewBox="0 0 36 24" fill="none" stroke="currentColor" strokeWidth="3">
                    <path d="M2 12h28M24 6l6 6-6 6"/>
                  </svg>
                </div>
              </div>

              {/* FederalRunner MCP Server */}
              <div className={`w-[320px] flex flex-col items-center transition-all duration-500 ${stage >= 3 ? 'opacity-100' : 'opacity-0'}`}>
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
                      <div className="flex items-center gap-2 text-xs text-gray-800">
                        <Chrome className="w-4 h-4 text-orange-600" />
                        <span className="font-semibold">Playwright headless</span>
                      </div>
                      <div className="ml-6 mt-1 space-y-0.5">
                        <div className="flex items-center gap-1.5 text-xs text-gray-700">
                          <div className="w-1 h-1 bg-green-400 rounded-full"></div>
                          <span>Atomic execution (8 sec)</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Arrows from MCP to Government Website and Auth0 */}
              <div className="flex flex-col h-full">
                {/* Arrow to Government Website - aligned to top */}
                <div className={`flex items-center px-2 mt-4 transition-all duration-500 ${stage >= 4 ? 'opacity-100' : 'opacity-0'}`}>
                  <div className="text-blue-500">
                    <svg width="36" height="24" viewBox="0 0 36 24" fill="none" stroke="currentColor" strokeWidth="3">
                      <path d="M2 12h28M24 6l6 6-6 6"/>
                    </svg>
                  </div>
                </div>
                
                {/* Arrow to Auth0 - pushed down with large margin */}
                <div className={`flex items-center px-2 mt-48 transition-all duration-500 ${stage >= 4 ? 'opacity-100' : 'opacity-0'}`}>
                  <div className="text-blue-500">
                    <svg width="36" height="24" viewBox="0 0 36 24" fill="none" stroke="currentColor" strokeWidth="3">
                      <path d="M2 12h28M24 6l6 6-6 6"/>
                    </svg>
                  </div>
                </div>
              </div>

              {/* Government Website + Auth0 - Now as separate build stages */}
              <div className="w-[380px] flex flex-col gap-3">
                {/* Government Website */}
                <div className={`flex flex-col items-center transition-all duration-500 ${stage >= 4 ? 'opacity-100' : 'opacity-0'}`}>
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
                <div className={`flex flex-col items-center transition-all duration-500 ${stage >= 4 ? 'opacity-100' : 'opacity-0'}`}>
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

      {/* Navigation hint */}
      <div className="text-center mt-4">
        <p className="text-sm text-gray-500">Use ← → arrow keys | Stage {stage + 1} of {maxStages + 1}</p>
      </div>
    </div>
  );
};

export default Phase2RemoteMCP;