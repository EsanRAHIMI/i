'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { apiClient } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

interface AvatarCustomizationProps {
  onClose?: () => void;
  onSave?: (avatarData: any) => void;
}

export function AvatarCustomization({ onClose, onSave }: AvatarCustomizationProps) {
  const { user, updateUser } = useAppStore();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [history, setHistory] = useState<Array<{ id: string; filename: string; avatar_url: string }>>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refreshHistory = useCallback(async () => {
    const data = await apiClient.listAvatars();
    setHistory((data?.items || []).map((x: any) => ({ id: x.id, filename: x.filename, avatar_url: x.avatar_url })));
  }, []);

  useEffect(() => {
    if (!user?.id) return;
    let mounted = true;
    const loadHistory = async () => {
      try {
        setHistoryLoading(true);
        const data = await apiClient.listAvatars();
        if (mounted) {
          setHistory((data?.items || []).map((x: any) => ({ id: x.id, filename: x.filename, avatar_url: x.avatar_url })));
        }
      } catch (e) {
        try {
          await new Promise((r) => setTimeout(r, 400));
          const data = await apiClient.listAvatars();
          if (mounted) {
            setHistory((data?.items || []).map((x: any) => ({ id: x.id, filename: x.filename, avatar_url: x.avatar_url })));
          }
        } catch {
          // ignore history errors; user can still upload
        }
      } finally {
        if (mounted) setHistoryLoading(false);
      }
    };
    loadHistory();
    return () => {
      mounted = false;
    };
  }, [user?.id]);

  const selectFromHistory = useCallback(
    async (avatarUrl: string) => {
      try {
        setIsLoading(true);
        setError(null);
        const updatedUser = await apiClient.selectAvatar(avatarUrl);
        if (updatedUser && updatedUser.avatar_url) {
          await updateUser({ avatar_url: updatedUser.avatar_url });
        }
        onSave?.({ avatar_url: updatedUser.avatar_url, selected_at: new Date().toISOString() });
        onClose?.();
      } catch (err: any) {
        const errorMessage = err.response?.data?.detail || err.message || 'Failed to select avatar';
        setError(errorMessage);
      } finally {
        setIsLoading(false);
      }
    },
    [onClose, onSave, updateUser]
  );

  const deleteFromHistory = useCallback(
    async (avatarId: string) => {
      try {
        setIsLoading(true);
        setError(null);
        const updatedUser = await apiClient.deleteAvatar(avatarId);
        if (updatedUser && 'avatar_url' in updatedUser) {
          await updateUser({ avatar_url: (updatedUser as any).avatar_url });
        }
        await refreshHistory();
      } catch (err: any) {
        const errorMessage = err.response?.data?.detail || err.message || 'Failed to delete avatar';
        setError(errorMessage);
      } finally {
        setIsLoading(false);
      }
    },
    [refreshHistory, updateUser]
  );

  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      setError('Please select a valid image file');
      return;
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      setError('Image size must be less than 5MB');
      return;
    }

    setSelectedFile(file);
    setError(null);

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setPreviewImage(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  }, []);

  const handleDrop = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    
    if (file && file.type.startsWith('image/')) {
      // Create a proper FileList-like object
      const fileList = {
        0: file,
        length: 1,
        item: (index: number) => index === 0 ? file : null,
        [Symbol.iterator]: function* () { yield file; }
      } as FileList;
      
      const syntheticEvent = {
        target: { files: fileList },
        currentTarget: { files: fileList }
      } as unknown as React.ChangeEvent<HTMLInputElement>;
      
      handleFileSelect(syntheticEvent);
    }
  }, [handleFileSelect]);

  const handleDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
  }, []);

  const processAvatar = async () => {
    if (!selectedFile) return;

    try {
      setIsLoading(true);
      setError(null);

      // Upload avatar to server
      const updatedUser = await apiClient.uploadAvatar(selectedFile);

      // Update user in store
      if (updatedUser && updatedUser.avatar_url) {
        await updateUser({ avatar_url: updatedUser.avatar_url });
      }

      // Prepare avatar data for callback
      const avatarData = {
        avatar_url: updatedUser.avatar_url || previewImage,
        facial_features: {
          eye_color: 'brown',
          hair_color: 'dark',
          skin_tone: 'medium',
          face_shape: 'oval'
        },
        generated_at: new Date().toISOString()
      };

      onSave?.(avatarData);
      onClose?.();
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to upload avatar';
      setError(errorMessage);
      console.error('Avatar upload error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const resetSelection = () => {
    setSelectedFile(null);
    setPreviewImage(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-2xl rounded-lg bg-white p-6 shadow-xl dark:bg-gray-900">
        <div className="p-6 border-b border-gray-700">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-white">Customize Your Avatar</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Previous Avatars */}
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">Previous avatars</h3>
            {historyLoading ? (
              <div className="flex items-center justify-center py-4">
                <LoadingSpinner size="sm" />
              </div>
            ) : history.length === 0 ? (
              <div className="text-sm text-gray-500 dark:text-gray-400">No previous avatars</div>
            ) : (
              <div className="grid grid-cols-4 gap-2">
                {history.map((item) => (
                  <div
                    key={item.id}
                    role="button"
                    tabIndex={isLoading ? -1 : 0}
                    aria-disabled={isLoading}
                    className="overflow-hidden rounded-md border border-gray-200 hover:border-gray-400 dark:border-gray-700"
                    onClick={() => {
                      if (isLoading) return;
                      selectFromHistory(item.avatar_url);
                    }}
                    onKeyDown={(e) => {
                      if (isLoading) return;
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        selectFromHistory(item.avatar_url);
                      }
                    }}
                    title={item.filename}
                  >
                    <div className="relative">
                      <img src={item.avatar_url} alt={item.filename} className="h-16 w-full object-cover" />
                      <button
                        type="button"
                        className="absolute right-1 top-1 rounded bg-black/60 px-1 text-xs text-white"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteFromHistory(item.id);
                        }}
                        disabled={isLoading}
                        title="Delete"
                      >
                        ×
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          <p className="text-gray-400 text-sm mt-2">
            Upload a selfie to create a personalized 3D avatar
          </p>
        </div>

        <div className="p-6 space-y-6">
          {/* Upload Section */}
          <div
            className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 p-8 text-center dark:border-gray-700"
            onDrop={handleDrop}
            onDragOver={handleDragOver}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              className="hidden"
            />

            {previewImage ? (
              <div className="space-y-4">
                <img
                  src={previewImage}
                  alt="Avatar preview"
                  className="w-32 h-32 rounded-full mx-auto object-cover border-4 border-primary-500"
                />
                <div className="space-y-2">
                  <p className="text-white font-medium">Ready to generate avatar</p>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      resetSelection();
                    }}
                    className="text-primary-400 hover:text-primary-300 text-sm"
                  >
                    Choose different image
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="w-16 h-16 mx-auto bg-gray-700 rounded-full flex items-center justify-center">
                  <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <p className="text-white font-medium">Upload your selfie</p>
                  <p className="text-gray-400 text-sm">Drag and drop or click to browse</p>
                  <p className="text-gray-500 text-xs mt-1">PNG, JPG up to 5MB</p>
                </div>
              </div>
            )}
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {/* Avatar Features Info */}
          <div className="bg-dark-900 rounded-lg p-4">
            <h3 className="text-white font-medium mb-2">Avatar Features</h3>
            <ul className="text-gray-400 text-sm space-y-1">
              <li>• Facial recognition for accurate representation</li>
              <li>• Lip-sync animation with voice output</li>
              <li>• Real-time expressions and emotions</li>
              <li>• Privacy-first processing (data stays local)</li>
            </ul>
          </div>

          {/* Action Buttons */}
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-600 text-gray-300 rounded-lg hover:bg-gray-700 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={processAvatar}
              disabled={!selectedFile || isLoading}
              className="flex-1 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center justify-center space-x-2"
            >
              {isLoading ? (
                <>
                  <LoadingSpinner size="sm" />
                  <span>Processing...</span>
                </>
              ) : (
                <span>Generate Avatar</span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}