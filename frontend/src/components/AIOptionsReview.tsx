'use client';

import React, { useState, useCallback } from 'react';
import { Brain, ArrowRight, Loader2, AlertTriangle } from 'lucide-react';
import StockSelector, { StockSelection } from './StockSelector';
import ExpirationSelector, { ExpirationDate } from './ExpirationSelector';
import StrategySelector, { StrategyProfile } from './StrategySelector';
import PositionSizer, { PositionSize } from './PositionSizer';
import styles from '@/styles/components.module.css';
import { api } from '../lib/api';

interface AIOptionsReviewProps {
  onAnalysisComplete?: (analysis: any) => void;
}

interface ReviewState {
  stock: StockSelection | null;
  expiration: ExpirationDate | null;
  strategy: StrategyProfile | null;
  position: PositionSize | null;
}

export default function AIOptionsReview({ onAnalysisComplete }: AIOptionsReviewProps) {
  const [reviewState, setReviewState] = useState<ReviewState>({
    stock: null,
    expiration: null,
    strategy: null,
    position: null
  });
  
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // Check if all required fields are completed
  const isReadyForAnalysis = () => {
    return reviewState.stock?.isValid && 
           reviewState.expiration && 
           reviewState.strategy && 
           reviewState.position &&
           reviewState.position.maxPositionSize > 0;
  };

  const handleStockSelected = useCallback((stock: StockSelection) => {
    setReviewState(prev => ({
      ...prev,
      stock,
      // Reset dependent fields when stock changes
      expiration: null
    }));
    setAnalysisError(null);
  }, []);

  const handleExpirationSelected = useCallback((expiration: ExpirationDate) => {
    setReviewState(prev => ({
      ...prev,
      expiration
    }));
    setAnalysisError(null);
  }, []);

  const handleStrategySelected = useCallback((strategy: StrategyProfile) => {
    setReviewState(prev => ({
      ...prev,
      strategy
    }));
    setAnalysisError(null);
  }, []);

  const handlePositionChanged = useCallback((position: PositionSize) => {
    setReviewState(prev => ({
      ...prev,
      position
    }));
    setAnalysisError(null);
  }, []);

  const handleAnalyzeOptions = async () => {
    if (!isReadyForAnalysis()) return;

    setIsAnalyzing(true);
    setAnalysisError(null);

    try {
      const analysisRequest = {
        symbol: reviewState.stock!.symbol,
        expiration_date: reviewState.expiration!.date,
        strategy_type: reviewState.strategy!.id,
        max_position_size: reviewState.position!.maxPositionSize,
        shares_owned: reviewState.position!.sharesOwned,
        account_size: reviewState.position!.accountSize
      };

      console.log('Analysis request:', analysisRequest);

      const response = await api.analyzeOptionsStrategy(analysisRequest);

      if (response.success) {
        const analysisResult = {
          symbol: reviewState.stock!.symbol,
          strategy: reviewState.strategy!.name,
          confidence: response.analysis.confidence_score || 0.75,
          recommendation: response.analysis.recommendation || 'HOLD',
          analysis: response.analysis,
          recommendations: response.recommendations,
          risk_analysis: response.risk_analysis,
          interactive_data: response.interactive_data,
          disclaimer: response.disclaimer
        };

        if (onAnalysisComplete) {
          onAnalysisComplete(analysisResult);
        }
      } else {
        setAnalysisError(response.error_message || 'Analysis failed');
      }

    } catch (error) {
      setAnalysisError('Analysis failed. Please try again.');
      console.error('Analysis error:', error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getProgressPercentage = () => {
    let completed = 0;
    if (reviewState.stock?.isValid) completed += 25;
    if (reviewState.expiration) completed += 25;
    if (reviewState.strategy) completed += 25;
    if (reviewState.position && reviewState.position.maxPositionSize > 0) completed += 25;
    return completed;
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      {/* Header */}
      <div className="text-center">
        <div className="flex items-center justify-center mb-4">
          <Brain className="h-8 w-8 text-[var(--accent-primary)] mr-3" />
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
            AI Options Review
          </h1>
        </div>
        <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
          Get a comprehensive "second opinion" on your options strategy with dual AI analysis. 
          Select your parameters below for personalized risk/reward insights.
        </p>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
        <div 
          className="bg-[var(--accent-primary)] h-2 rounded-full transition-all duration-300"
          style={{ width: `${getProgressPercentage()}%` }}
        ></div>
      </div>
      <div className="text-center text-sm text-gray-600 dark:text-gray-400">
        {getProgressPercentage()}% Complete
      </div>

      {/* Step 1: Stock Selection */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center mb-4">
          <div className="w-8 h-8 bg-[var(--accent-primary)] text-white rounded-full flex items-center justify-center font-semibold mr-3">
            1
          </div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Choose Your Stock
          </h2>
        </div>
        
        <StockSelector
          onStockSelected={handleStockSelected}
          selectedStock={reviewState.stock}
          disabled={isAnalyzing}
        />
      </div>

      {/* Step 2: Expiration Selection */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center mb-4">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center font-semibold mr-3 ${
            reviewState.stock?.isValid 
              ? 'bg-[var(--accent-primary)] text-white' 
              : 'bg-gray-300 dark:bg-gray-600 text-gray-500'
          }`}>
            2
          </div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Select Expiration Date
          </h2>
        </div>
        
        <ExpirationSelector
          symbol={reviewState.stock?.symbol || null}
          onExpirationSelected={handleExpirationSelected}
          selectedExpiration={reviewState.expiration}
          disabled={!reviewState.stock?.isValid || isAnalyzing}
        />
      </div>

      {/* Step 3: Strategy Selection */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center mb-4">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center font-semibold mr-3 ${
            reviewState.expiration 
              ? 'bg-[var(--accent-primary)] text-white' 
              : 'bg-gray-300 dark:bg-gray-600 text-gray-500'
          }`}>
            3
          </div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Choose Trading Strategy
          </h2>
        </div>
        
        <StrategySelector
          onStrategySelected={handleStrategySelected}
          selectedStrategy={reviewState.strategy}
          disabled={!reviewState.expiration || isAnalyzing}
        />
      </div>

      {/* Step 4: Position Sizing */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center mb-4">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center font-semibold mr-3 ${
            reviewState.strategy 
              ? 'bg-[var(--accent-primary)] text-white' 
              : 'bg-gray-300 dark:bg-gray-600 text-gray-500'
          }`}>
            4
          </div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Set Position Size
          </h2>
        </div>
        
        <PositionSizer
          onPositionChanged={handlePositionChanged}
          selectedPosition={reviewState.position}
          disabled={!reviewState.strategy || isAnalyzing}
          currentStockPrice={reviewState.stock?.currentPrice}
        />
      </div>

      {/* Analysis Button */}
      <div className="text-center">
        {analysisError && (
          <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <div className="flex items-center justify-center text-red-700 dark:text-red-300">
              <AlertTriangle className="h-4 w-4 mr-2" />
              {analysisError}
            </div>
          </div>
        )}

        <button
          onClick={handleAnalyzeOptions}
          disabled={!isReadyForAnalysis() || isAnalyzing}
          className={`px-8 py-4 text-lg font-semibold rounded-lg transition-all ${
            isReadyForAnalysis() && !isAnalyzing
              ? 'bg-[var(--accent-primary)] text-white hover:bg-[var(--accent-primary)]/90 hover:scale-105 shadow-lg'
              : 'bg-gray-300 dark:bg-gray-600 text-gray-500 cursor-not-allowed'
          }`}
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="h-5 w-5 mr-3 animate-spin inline" />
              Analyzing with Dual AI...
            </>
          ) : (
            <>
              <Brain className="h-5 w-5 mr-3 inline" />
              Get AI Options Analysis
              <ArrowRight className="h-5 w-5 ml-3 inline" />
            </>
          )}
        </button>

        {!isReadyForAnalysis() && (
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
            Complete all steps above to enable analysis
          </p>
        )}
      </div>

      {/* Disclaimer */}
      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
        <div className="text-sm text-yellow-700 dark:text-yellow-300">
          <strong>Important Disclaimer:</strong> This tool provides educational analysis and is not financial advice. 
          Options trading involves significant risk and may not be suitable for all investors. 
          Always do your own research and consider consulting with a financial advisor.
        </div>
      </div>
    </div>
  );
}
